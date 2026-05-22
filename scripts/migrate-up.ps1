param(
    [string]$Revision = "head"
)

python -m alembic upgrade $Revision
