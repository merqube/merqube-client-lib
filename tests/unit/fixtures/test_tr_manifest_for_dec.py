from merqube_client_lib.pydantic_v2_types import IndexDefinitionPatchPutGet as Index

tr = Index.parse_obj(
    {
        "administrative": {"role": "development"},
        "base_date": "2005/12/30",
        "currency": "EUR",
        "description": "MerQube AXAF.PA TR Index",
        "documents": {"dividends": "tr/MQU_AXAF_TR_Index_Test_1_dividend_report.csv"},
        "family": "MerQube Single Stock TR indices",
        "family_description": "MerQube Single Stock TR indices",
        "id": "01377447-e1ef-4275-908a-b511a3aeb7ad",
        "identifiers": [],
        "launch_date": "2023/06/01",
        "name": "MQU_AXAF_TR_Index_Test_1",
        "namespace": "merqubetr",
        "related": [],
        "run_configuration": {
            "index_reports": [
                {
                    "program_args": {
                        "diss_config": '{\\"email\\": [{\\"files\\": [\\"levels\\", \\"close_portfolio\\", \\"corporate_actions\\", \\"proforma_portfolio\\"], \\"subject\\": \\"{INDEX_NAME} Report: {REPORT_DATE:%Y-%m-%d}\\", \\"recipients\\": [\\"data@merqube.com\\", \\"tommy@merqube.com\\", \\"tianyin@merqube.com\\"]}]}'
                    },
                    "uuid": "e79c6ea1-2ad0-429c-a4f0-b89915c1839e",
                }
            ],
            "job_enabled": True,
            "num_days_to_load": 100,
            "pod_image_and_tag": "merq-310:latest",
            "schedule": {"retries": 25, "retry_interval_min": 10, "schedule_start": "2023-07-12T18:54:00"},
            "tzinfo": "UTC",
        },
        "spec": {
            "index_class": "merq.indices.merqube.equity.EquityBasketIndex",
            "index_class_args": {
                "spec": {
                    "base_date": "2005-12-30",
                    "base_val": 1000,
                    "calendar": {"calendar_identifiers": ["MIC:XPAR"]},
                    "corporate_actions": {
                        "dividend": {"deduct_tax": False, "reinvest_day": "PREV_DAY", "reinvest_strategy": "IN_INDEX"}
                    },
                    "currency": "EUR",
                    "holiday_spec": {"calendar_identifiers": ["MIC:XPAR"]},
                    "index_id": "MQU_AXAF_TR_Index_Test_1",
                    "portfolios": {
                        "constituents": [{"date": "2005-12-30", "identifier": "AXAF.PA", "amount": 1}],
                        "date_type": "ROLL",
                        "identifier_type": "RIC",
                        "amount_type": "WEIGHT",
                        "specification_type": "INLINE",
                    },
                }
            },
        },
        "stage": "prod",
        "status": {
            "created_at": "2023-07-17T14:25:08.698178",
            "created_by": "fooy@merqube.com",
            "last_modified": "2023-07-18T04:30:51.616683",
            "last_modified_by": "foo@merqube.com",
        },
        "title": "MerQube AXAF.PA TR Index",
    }
)
