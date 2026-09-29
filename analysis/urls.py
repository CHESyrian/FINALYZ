from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    path("", views.home, name="home"),
    path("demo/", views.demo, name="demo"),
    path("manual/", views.manual_input, name="manual_input"),
    path("excel/", views.excel_upload, name="excel_upload"),
    path("excel/mapping/", views.excel_mapping, name="excel_mapping"),
    path("compare/", views.compare_periods_view, name="compare"),
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("ai/", views.ai_commentary, name="ai_commentary"),
    path("report/session/", views.report_from_session, name="report_from_session"),
    path("whatif/", views.whatif_simulate, name="whatif"),
    path("set-language/", views.set_language, name="set_language"),
]
