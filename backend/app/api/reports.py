"""Report endpoints: list reports and fetch the latest / a specific one."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import ReportDetail, ReportSummary
from app.db.base import get_db
from app.models import Report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
def list_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


# Defined before "/{report_id}" so "latest" is not parsed as an id.
@router.get("/latest", response_model=ReportDetail)
def latest_report(db: Session = Depends(get_db)):
    report = db.scalars(
        select(Report).order_by(Report.created_at.desc()).limit(1)
    ).first()
    if report is None:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return report


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
