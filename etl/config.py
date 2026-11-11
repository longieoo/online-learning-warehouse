"""Kết nối và giới hạn tài nguyên của các tiến trình kho dữ liệu."""

import os

import clickhouse_connect
import psycopg2


def pg_connect():
    return psycopg2.connect(application_name="online_learning_dw", connect_timeout=15)


def staging_connect():
    return psycopg2.connect(
        dbname="dwh_staging",
        user="learning_stage",
        password=os.environ["PG_STAGE_PASSWORD"],
        application_name="online_learning_dw",
        connect_timeout=15,
    )


def source_connect():
    return psycopg2.connect(
        dbname="learning_oltp",
        user="learning_reader",
        password=os.environ["PG_READER_PASSWORD"],
        application_name="dw_readonly",
        connect_timeout=15,
    )


def ch_connect():
    return clickhouse_connect.get_client(
        host=os.getenv("CH_HOST", "localhost"),
        port=int(os.getenv("CH_PORT", "8123")),
        username=os.getenv("CH_USER", "learning"),
        password=os.environ["CH_PASSWORD"],
        connect_timeout=30,
        send_receive_timeout=600,
        settings={
            "max_threads": 4,
            "max_memory_usage": 1800000000,
            "max_bytes_before_external_group_by": 500000000,
            "max_bytes_before_external_sort": 500000000,
        },
    )
