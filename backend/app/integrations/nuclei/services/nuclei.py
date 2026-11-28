from typing import Optional
from typing import Type
from typing import TypeVar

import httpx
from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from pydantic import ValidationError

from app.integrations.nuclei.schema.nuclei import DeleteNucleiReportResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportCollectionResponse
from app.integrations.nuclei.schema.nuclei import NucleiReportsAvailableResponse
from app.integrations.nuclei.schema.nuclei import NucleiScanRequest
from app.integrations.nuclei.schema.nuclei import NucleiScanResponse

NUCLEI_MODULE_URL = "http://copilot-nuclei-module"
NUCLEI_REQUEST_TIMEOUT = 15
NUCLEI_UNAVAILABLE_MESSAGE = "Dịch vụ đánh giá web chưa sẵn sàng"
NUCLEI_BAD_RESPONSE_MESSAGE = "Dịch vụ đánh giá web trả về dữ liệu không hợp lệ"
NUCLEI_REPORTS_NOT_FOUND_MESSAGE = "Không tìm thấy báo cáo đánh giá web"
NUCLEI_REPORT_NOT_FOUND_MESSAGE = "Không tìm thấy báo cáo đánh giá web này"

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


async def _call_nuclei_module(
    method: str,
    path: str,
    response_model: Type[ResponseModel],
    not_found_detail: Optional[str] = None,
    **kwargs,
) -> ResponseModel:
    """
    Call the Nuclei module and parse its answer.

    Network failures and 5xx answers become a 503, an answer that is not the expected document becomes a 502.
    The user-facing messages carry no host or upstream body; the details go to the log.
    """
    url = f"{NUCLEI_MODULE_URL}{path}"
    kwargs.setdefault("timeout", NUCLEI_REQUEST_TIMEOUT)
    try:
        async with httpx.AsyncClient() as client:
            response = await getattr(client, method)(url, **kwargs)
    except httpx.HTTPError as e:
        logger.error(f"Nuclei module request {method.upper()} {url} failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail=NUCLEI_UNAVAILABLE_MESSAGE)

    if response.status_code == 404 and not_found_detail:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if response.status_code >= 500:
        logger.error(f"Nuclei module {method.upper()} {url} answered {response.status_code}: {response.text[:500]}")
        raise HTTPException(status_code=503, detail=NUCLEI_UNAVAILABLE_MESSAGE)
    if response.status_code >= 400:
        logger.error(f"Nuclei module {method.upper()} {url} answered {response.status_code}: {response.text[:500]}")
        raise HTTPException(status_code=502, detail=NUCLEI_BAD_RESPONSE_MESSAGE)

    try:
        return response_model(**response.json())
    except (ValueError, TypeError, ValidationError) as e:
        logger.error(f"Nuclei module {method.upper()} {url} returned an unexpected document: {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=NUCLEI_BAD_RESPONSE_MESSAGE)


async def get_nuclei_reports_available() -> NucleiReportsAvailableResponse:
    """
    Retrieve the list of available Nuclei reports.

    Returns:
        NucleiReportsAvailableResponse: The response containing the list of available Nuclei reports.
    """
    logger.info(f"Sending GET request to {NUCLEI_MODULE_URL}/all_reports")
    return await _call_nuclei_module("get", "/all_reports", NucleiReportsAvailableResponse, NUCLEI_REPORTS_NOT_FOUND_MESSAGE)


async def get_nuclei_report(host: str, report: str = "index.md") -> NucleiReportCollectionResponse:
    """
    Retrieve a specific Nuclei report.

    Args:
        host (str): The host to retrieve the report for.
        report (str): The report to retrieve. Defaults to "index.md".

    Returns:
        NucleiReportCollectionResponse: The response containing the Nuclei report.
    """
    logger.info(f"Sending GET request to {NUCLEI_MODULE_URL}/report/{host}/{report}")
    return await _call_nuclei_module("get", f"/report/{host}/{report}", NucleiReportCollectionResponse, NUCLEI_REPORT_NOT_FOUND_MESSAGE)


async def delete_nuclei_report(host: str) -> DeleteNucleiReportResponse:
    """
    Delete a specific Nuclei report.

    Args:
        host (str): The host to delete the report for.

    Returns:
        DeleteNucleiReportResponse: The response containing the result of the deletion.
    """
    logger.info(f"Sending DELETE request to {NUCLEI_MODULE_URL}/report/{host}")
    return await _call_nuclei_module("delete", f"/report/{host}", DeleteNucleiReportResponse, NUCLEI_REPORT_NOT_FOUND_MESSAGE)


async def post_to_copilot_nuclei_module(data: NucleiScanRequest) -> NucleiScanResponse:
    """
    Send a POST request to the copilot-nuclei-module Docker container.

    Args:
        data (NucleiScanRequest): The data to send to the copilot-nuclei-module Docker container.
    """
    logger.info(f"Sending POST request to {NUCLEI_MODULE_URL}/scan with data: {data.model_dump()}")
    return await _call_nuclei_module("post", "/scan", NucleiScanResponse, json=data.model_dump(), timeout=120)
