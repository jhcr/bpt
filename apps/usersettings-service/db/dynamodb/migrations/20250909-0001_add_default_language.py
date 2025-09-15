"""Add default language setting to existing user settings"""


def up(ddb):
    """Migration: Add default language 'en' to all existing user settings"""
    table_name = "user_settings_dev"  # TODO: Make environment configurable
    t = ddb.Table(table_name)

    # Scan for all existing items
    scan = t.scan(ProjectionExpression="user_id, #c", ExpressionAttributeNames={"#c": "category"})

    for item in scan.get("Items", []):
        # Add default language if not exists
        t.update_item(
            Key={"user_id": item["user_id"], "category": item["category"]},
            UpdateExpression="SET #d.#lang = if_not_exists(#d.#lang, :en)",
            ExpressionAttributeNames={"#d": "data", "#lang": "language"},
            ExpressionAttributeValues={":en": "en"},
        )
