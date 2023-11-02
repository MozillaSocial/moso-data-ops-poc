from typing import Optional

from prefect_snowflake import SnowflakeConnector, SnowflakeCredentials
from pydantic import BaseModel, PrivateAttr, SecretBytes, SecretStr, constr

from common.settings import CommonSettings, NestedSettings, Settings

CS = CommonSettings()  # type: ignore

# we want to make sure proper warehouses are used
# could be changed to a Literal list or enum later
WAREHOUSE_REGEX = "^(?i)prefect.*?"

class SnowflakeCredSettings(NestedSettings):
    """Settings that can be passed in for
    Snowflake Credentials.  This is mean to be used as
    a sub model of the SnowflakeSetting model.
    """

    account: str
    user: str
    private_key_passphrase: Optional[SecretStr]
    private_key: Optional[SecretBytes]
    private_key_path: Optional[str]
    role: str


class SnowflakeSettings(Settings):
    """Settings for Snowflake Connection.  Database can only be 'development'
    or 'prefect' depending on CommonSetings.dev_or_production property value.

    These must be set using DF_CONFIG_<field_name> envars.

    This is for the initial connection only.  Normal Snowflake
    methods for changing things on execution still work.

    See pytest.ini at the common-utils root for examples.
    """

    snowflake_credentials: SnowflakeCredSettings
    _database: str = PrivateAttr()
    snowflake_warehouse: constr(regex=WAREHOUSE_REGEX) = f"prefect_wh_{CS.dev_or_production}"  # type: ignore  # noqa: E501
    snowflake_schema: str = "public"
    snowflake_gcp_stages: Optional[dict]

    def __init__(self, **data):
        super().__init__(**data)
        db = "development"
        if CS.is_production:
            db = "prefect"
        self._database = db

    @property
    def database(self):
        return self._database


class MozSnowflakeConnector(SnowflakeConnector):
    """Mozilla version of the Snowflake Connector provided
    by Prefect-Snowflake with credentials and other settings already applied.
    schema and warehouse must be set via envars.
    All other base model attributes can be set explicitly here.

    Warehouse is overriden to enforce our regex in settings.

    See https://prefecthq.github.io/prefect-snowflake/ for usage.
    """

    def __init__(self, **data):
        """Set credentials and other settings on usage of
        model.  SnowflakeSettings values for schema and warehouse
        are given preference.
        """
        settings = SnowflakeSettings()  # type: ignore
        data["database"] = settings.database
        data["credentials"] = SnowflakeCredentials(
            **settings.snowflake_credentials.dict()
        )

        schema = data.get("schema", settings.snowflake_schema)
        warehouse = data.get("warehouse", settings.snowflake_warehouse)

        data["schema"] = schema
        data["warehouse"] = warehouse
        super().__init__(**data)

