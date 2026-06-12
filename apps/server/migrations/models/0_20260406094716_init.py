from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "extracted_parameters" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "raw_response" JSON
);
CREATE TABLE IF NOT EXISTS "fund_mandates" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "legal_name" VARCHAR(255) NOT NULL,
    "strategy_type" VARCHAR(255) NOT NULL,
    "vintage_year" INT NOT NULL,
    "primary_analyst" VARCHAR(500) NOT NULL,
    "processing_date" TIMESTAMP,
    "target_count" INT,
    "description" TEXT,
    "extracted_parameters_id" INT REFERENCES "extracted_parameters" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "companies" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "company_name" VARCHAR(500) NOT NULL,
    "country" VARCHAR(128),
    "sector" VARCHAR(128),
    "industry" VARCHAR(256),
    "revenue" REAL,
    "dividend_yield" VARCHAR(64),
    "five_years_growth" REAL,
    "net_income" REAL,
    "total_assets" REAL,
    "total_equity" REAL,
    "eps_forecast" VARCHAR(128),
    "ebitda" VARCHAR(128),
    "one_year_change" VARCHAR(64),
    "pe_ratio" REAL,
    "debt_equity" REAL,
    "price_book" REAL,
    "return_on_equity" REAL,
    "market_cap" VARCHAR(128),
    "gross_profit_margin" VARCHAR(64),
    "risks" JSON,
    "attributes" JSON,
    "fund_mandate_id" INT REFERENCES "fund_mandates" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "generated_documents" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "generated_content" TEXT NOT NULL,
    "fund_mandate_id" INT NOT NULL REFERENCES "fund_mandates" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "risk_analysis" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "parameter_analysis" JSON,
    "overall_result" VARCHAR(50),
    "overall_assessment" JSON,
    "company_id" INT REFERENCES "companies" ("id") ON DELETE CASCADE,
    "fund_mandate_id" INT REFERENCES "fund_mandates" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "risk_parameters" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(256) NOT NULL,
    "value" TEXT NOT NULL,
    "extracted_parameters_id" INT REFERENCES "extracted_parameters" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "screening" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "selected_parameters" JSON NOT NULL,
    "status" VARCHAR(50),
    "reason" TEXT,
    "raw_agent_output" TEXT,
    "company_id" INT REFERENCES "companies" ("id") ON DELETE CASCADE,
    "fund_mandate_id" INT REFERENCES "fund_mandates" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "screening_parameters" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(256) NOT NULL,
    "value" TEXT NOT NULL,
    "extracted_parameters_id" INT REFERENCES "extracted_parameters" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "sourcing" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "company_id" INT NOT NULL,
    "company_data" JSON NOT NULL,
    "selected_parameters" JSON NOT NULL,
    "fund_mandate_id" INT NOT NULL REFERENCES "fund_mandates" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "sourcing_parameters" (
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMP,
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "key" VARCHAR(256) NOT NULL,
    "value" TEXT NOT NULL,
    "extracted_parameters_id" INT REFERENCES "extracted_parameters" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "sourcing_companies" (
    "sourcing_id" INT NOT NULL REFERENCES "sourcing" ("id") ON DELETE CASCADE,
    "company_id" INT NOT NULL REFERENCES "companies" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_sourcing_co_sourcin_f93269" ON "sourcing_companies" ("sourcing_id", "company_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "kw=="
)
