"""Collection-status constants shared by the ETL and the dashboard.

The dashboard's status chip (:mod:`dashboard.components.layout`) maps a
``data_collection_log.status`` value to a chip tone. It must not import the
Bronze writer (:mod:`src.etl.bronze`), which pulls the ORM schema and the ETL
stack into a read-only deploy. The three status strings live here; the Bronze
writer imports them back, so its public surface is unchanged.
"""

STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
