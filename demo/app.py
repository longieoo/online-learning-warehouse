"""Source-backed analytics workspace for the local learning warehouse."""

import json
import logging
import subprocess
import sys
from datetime import date
from html import escape
from itertools import count
from contextlib import contextmanager

import pandas as pd
import streamlit as st
from demo.charts import (
    short_number,
    revenue_chart,
    ranked_chart,
    enrollment_chart,
    payment_mix,
    revenue_bridge,
    METHOD_LABELS,
)
from demo.data import options, snapshot, detail
from demo.presentation import metrics, card_title, empty, progress, ratio, percent, change, icon
from etl.common import ROOT

PAGES = ["Tổng quan", "Tài chính", "Học tập", "Đề thi", "Thị trường", "Chất lượng & vận hành"]
_cards = count()


@contextmanager
def card():
    with st.container(border=True, key=f"card_{next(_cards)}"):
        st.markdown('<span class="card-anchor"></span>', unsafe_allow_html=True)
        yield


st.set_page_config(
    page_title="Learning Warehouse · Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    "<style>" + (ROOT / "demo/styles.css").read_text(encoding="utf-8") + "</style>",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60, show_spinner="Đang tải dữ liệu phân tích…")
def load_data(run_id, start, end, categories):
    return snapshot(run_id, start, end, categories)


@st.cache_data(ttl=60, show_spinner="Đang tải phân tích chi tiết…")
def load_detail(run_id, kind, start, end, categories):
    return detail(run_id, kind, start, end, categories)


def plot(figure, key):
    st.plotly_chart(
        figure,
        use_container_width=True,
        key=key,
        config={
            "displaylogo": False,
            "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
        },
    )


def table(frame, key, renames=None):
    display = frame.rename(columns=renames or {})
    st.dataframe(
        display.style.format(precision=2, na_rep="—"),
        use_container_width=True,
        hide_index=True,
        height=min(380, 38 + len(display) * 35),
    )
    filename = f"{key}_{start.isoformat()}_{end.isoformat()}.csv"
    st.download_button(
        "Xuất CSV",
        display.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        key="export_" + key,
    )


def reset_filters():
    st.session_state["period"] = str(bounds[1].year)
    st.session_state["categories"] = categories
    st.session_state["custom_dates"] = (date(2022, 1, 1), date(2024, 12, 31))


with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">'
        + icon("chart")
        + '</div><div><div class="brand-name">Learning Warehouse</div><div class="brand-sub">ANALYTICS WORKSPACE</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="nav-caption">KHÔNG GIAN PHÂN TÍCH</div>', unsafe_allow_html=True)
    page = st.radio("Điều hướng", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="nav-caption">DỮ LIỆU</div>', unsafe_allow_html=True)
    if st.button("↻  Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    manifest, categories, bounds = options()
except Exception:
    st.title("Kho dữ liệu đang được chuẩn bị")
    st.info("Dữ liệu đang nạp hoặc chưa sẵn sàng. Bạn có thể làm mới sau khi lần nạp hoàn tất.")
    st.stop()

with st.sidebar:
    published_at = pd.to_datetime(manifest["finished_at"], utc=True).strftime(
        "%d/%m/%Y · %H:%M UTC"
    )
    st.markdown(
        '<div class="sidebar-meta">Cập nhật bản dữ liệu<br><strong>'
        + published_at
        + "</strong><br><br>"
        + f"{sum(manifest['tables'].values()):,}".replace(",", ".")
        + " dòng đã chuẩn hóa<br>Kỳ sự kiện <strong>2022 – 2024</strong></div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="sidebar-meta">Nguồn dữ liệu giả lập<br>Tiền tệ VND · Múi giờ UTC</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="page-top"><div class="breadcrumb">Phân tích <span style="padding:0 7px">/</span><b>'
    + escape(page)
    + '</b></div><div class="publish-tag"><span class="status-dot"></span>Đã đối soát · '
    + str(manifest["quality_checks"])
    + " kiểm tra</div></div>",
    unsafe_allow_html=True,
)
st.title(page)

if "period" not in st.session_state:
    st.session_state["period"] = str(bounds[1].year)
if "categories" not in st.session_state:
    st.session_state["categories"] = categories
with st.container(key="filterbar"):
    st.markdown('<span class="filter-anchor"></span>', unsafe_allow_html=True)
    first, second, third = st.columns([1.25, 1.45, 0.65])
    with first:
        periods = [str(year) for year in range(bounds[1].year, 2021, -1)] + [
            "Toàn kỳ 2022–2024",
            "Tùy chọn",
        ]
        period = st.selectbox(
            "Kỳ phân tích", periods, key="period", disabled=page == "Chất lượng & vận hành"
        )
    with second:
        selected = st.session_state["categories"]
        label = (
            "Tất cả lĩnh vực"
            if len(selected) == len(categories)
            else (selected[0] if len(selected) == 1 else f"{len(selected)} lĩnh vực")
        )
        st.caption("Lĩnh vực khóa học")
        with st.popover(label, use_container_width=True, disabled=page == "Chất lượng & vận hành"):
            st.multiselect("Lĩnh vực khóa học", categories, key="categories")
    with third:
        st.button("Đặt lại", on_click=reset_filters, use_container_width=True)
    if period == "Tùy chọn":
        chosen = st.date_input(
            "Từ ngày – đến ngày",
            min_value=date(2022, 1, 1),
            max_value=date(2024, 12, 31),
            value=(date(2022, 1, 1), date(2024, 12, 31)),
            key="custom_dates",
        )
        if len(chosen) != 2:
            st.info("Chọn đủ ngày bắt đầu và ngày kết thúc.")
            st.stop()
        start, end = chosen
    elif period.startswith("Toàn kỳ"):
        start, end = date(2022, 1, 1), date(2024, 12, 31)
    else:
        start, end = date(int(period), 1, 1), date(int(period), 12, 31)
        if int(period) == bounds[1].year:
            end = min(end, bounds[1])
selected_categories = st.session_state["categories"]
if page == "Chất lượng & vận hành":
    start, end, selected_categories = date(2022, 1, 1), date(2024, 12, 31), categories
if not selected_categories:
    empty("Chọn ít nhất một lĩnh vực trong bộ lọc để bắt đầu phân tích.")
    st.stop()
if page == "Chất lượng & vận hành":
    st.markdown(
        '<div class="scope-caption">Trạng thái toàn kho · Bộ lọc phân tích không áp dụng cho trang này</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="scope-caption">'
        + f"{start:%d/%m/%Y} — {end:%d/%m/%Y} · {len(selected_categories)} lĩnh vực"
        + "</div>",
        unsafe_allow_html=True,
    )

try:
    data = load_data(manifest["run_id"], start, end, selected_categories)
except Exception:
    logging.exception("Dashboard snapshot failed")
    st.error("Không thể tải bản dữ liệu. Hãy làm mới sau khi quá trình nạp kết thúc.")
    st.stop()

monthly = data["finance"].copy()
funnel = data["funnel"].iloc[0]
net = int(monthly.net_vnd.sum())
gross = int(monthly.gross_vnd.sum())
payments = int(monthly.payments.sum())
completion = ratio(funnel.completed, funnel.enrolled)
prior = data["baseline"]
prior_rate = ratio(prior["completed"], prior["enrolled"]) if prior else None
comparison_note = "so với cùng kỳ " + str(prior["start"].year) if prior else "Trong kỳ đã chọn"


def headline():
    metrics(
        [
            dict(
                label="Doanh thu ròng",
                value=short_number(net, 2) + " ₫",
                icon="money",
                delta=change(net, prior["net_vnd"]) if prior else None,
                note=comparison_note,
            ),
            dict(
                label="Giao dịch thanh toán",
                value=f"{payments:,}".replace(",", "."),
                icon="chart",
                delta=change(payments, prior["payments"]) if prior else None,
                note=comparison_note,
            ),
            dict(
                label="Lượt ghi danh",
                value=f"{int(funnel.enrolled):,}".replace(",", "."),
                icon="users",
                delta=change(funnel.enrolled, prior["enrolled"]) if prior else None,
                note=comparison_note,
            ),
            dict(
                label="Tỷ lệ hoàn thành",
                value=percent(completion),
                icon="check",
                delta=change(completion, prior_rate, points=True)
                if completion is not None and prior_rate is not None
                else None,
                note="Theo cohort ghi danh",
            ),
        ]
    )


if page == "Tổng quan":
    headline()
    left, right = st.columns([1.65, 1], gap="medium")
    with left, card():
        title, control = st.columns([2.5, 1])
        with title:
            card_title("Diễn biến doanh thu", "Doanh thu ròng và giá trị giao dịch trước giảm giá")
        with control:
            grain = st.selectbox(
                "Nhóm thời gian",
                ["Tháng", "Quý"],
                key="revenue_grain",
                label_visibility="collapsed",
            )
        if monthly.empty:
            empty()
        else:
            plot(revenue_chart(monthly, grain), "overview_revenue")
    with right, card():
        card_title(
            "Doanh thu theo lĩnh vực",
            "Doanh thu ròng · VND",
            tag=f"{len(data['revenue_categories'])} lĩnh vực",
        )
        if data["revenue_categories"].empty:
            empty()
        else:
            plot(
                ranked_chart(data["revenue_categories"], "net_vnd", "category", height=310),
                "overview_categories",
            )
    left, right = st.columns([1.65, 1], gap="medium")
    with left, card():
        card_title("Ghi danh theo tháng", "Số lượt ghi danh trong kỳ")
        if data["enrollment_trend"].empty:
            empty()
        else:
            plot(enrollment_chart(data["enrollment_trend"]), "overview_enrollments")
    with right, card():
        card_title("Phương thức thanh toán", "Cơ cấu theo số giao dịch")
        if data["methods"].empty:
            empty()
        else:
            plot(payment_mix(data["methods"]), "overview_methods")

elif page == "Tài chính":
    metrics(
        [
            dict(
                label="Doanh thu ròng",
                value=short_number(net, 2) + " ₫",
                icon="money",
                delta=change(net, prior["net_vnd"]) if prior else None,
                note=comparison_note,
            ),
            dict(label="Giá trị giao dịch gốc", value=short_number(gross, 2) + " ₫", icon="chart"),
            dict(
                label="Tỷ lệ giảm giá",
                value=percent(ratio(monthly.discount_vnd.sum(), gross)),
                icon="money",
                note="Giảm giá / giá trị gốc",
            ),
            dict(
                label="Tỷ lệ hoàn tiền",
                value=percent(ratio(monthly.refunds.sum(), payments)),
                icon="check",
                note="Giao dịch hoàn / thanh toán",
            ),
        ]
    )
    with card():
        card_title("Doanh thu theo thời gian", "VND · Theo ngày thanh toán")
        if monthly.empty:
            empty()
        else:
            plot(revenue_chart(monthly), "finance_revenue")
    left, right = st.columns([1.55, 1], gap="medium")
    with left, card():
        card_title("Từ giá trị gốc đến doanh thu ròng", "Hoàn tiền được quy về ngày thanh toán gốc")
        if monthly.empty:
            empty()
        else:
            plot(revenue_bridge(monthly), "finance_bridge")
    with right, card():
        card_title("Doanh thu theo phương thức", "Doanh thu ròng · VND")
        methods = data["methods"].copy()
        methods["method"] = methods.method_name.map(lambda name: METHOD_LABELS.get(name, name))
        if methods.empty:
            empty()
        else:
            plot(ranked_chart(methods, "net_vnd", "method", height=280), "finance_methods")
    with st.expander("Chi tiết doanh thu và xuất dữ liệu"):
        table(
            monthly,
            "doanh_thu",
            {
                "month": "Tháng",
                "net_vnd": "Doanh thu ròng (₫)",
                "gross_vnd": "Giá trị gốc (₫)",
                "discount_vnd": "Giảm giá (₫)",
                "refund_vnd": "Hoàn tiền (₫)",
                "payments": "Giao dịch",
                "refunds": "Giao dịch hoàn",
            },
        )

elif page == "Học tập":
    metrics(
        [
            dict(
                label="Lượt ghi danh",
                value=f"{int(funnel.enrolled):,}".replace(",", "."),
                icon="users",
            ),
            dict(
                label="Bắt đầu học",
                value=percent(ratio(funnel.started, funnel.enrolled)),
                icon="book",
                note="Có ít nhất một bài hoàn thành",
            ),
            dict(
                label="Hoàn thành khóa",
                value=percent(completion),
                icon="check",
                note=f"{int(funnel.completed):,} lượt hoàn thành".replace(",", "."),
            ),
            dict(
                label="Thời gian hoàn thành",
                value=f"{funnel.avg_days:.1f}".replace(".", ",") + " ngày"
                if pd.notna(funnel.avg_days)
                else "—",
                icon="clock",
                note="Trung bình của lượt đã hoàn thành",
            ),
        ]
    )
    st.caption(
        "Cohort gồm lượt ghi danh trong kỳ. Trạng thái hoàn thành tính đến bản dữ liệu hiện tại, kể cả hoàn thành sau kỳ đã chọn."
    )
    left, right = st.columns([1, 1], gap="medium")
    with left, card():
        card_title("Hành trình học tập", "Số lượt ghi danh tại từng giai đoạn")
        progress(
            [
                ("Ghi danh", int(funnel.enrolled)),
                ("Bắt đầu học", int(funnel.started)),
                ("Hoàn thành", int(funnel.completed)),
            ]
        )
    with right, card():
        card_title("Hoàn thành theo lĩnh vực", "Hoàn thành / ghi danh · %")
        if data["courses"].empty:
            empty()
        else:
            plot(
                ranked_chart(
                    data["courses"].sort_values("completion_pct", ascending=False),
                    "completion_pct",
                    "category",
                    "percent",
                    height=255,
                ),
                "learning_completion",
            )
    with card():
        card_title("Ghi danh theo cohort tháng", "Cột thể hiện số lượt ghi danh")
        if data["enrollment_trend"].empty:
            empty()
        else:
            plot(enrollment_chart(data["enrollment_trend"]), "learning_trend")
    with st.expander("Chi tiết kết quả học tập"):
        table(
            data["courses"],
            "hoan_thanh",
            {
                "category": "Lĩnh vực",
                "enrollments": "Ghi danh",
                "completions": "Hoàn thành",
                "completion_pct": "Hoàn thành (%)",
            },
        )

elif page == "Đề thi":
    quiz = data["quiz"].copy()
    attempts = int(quiz.attempts.sum())
    metrics(
        [
            dict(label="Lượt làm bài", value=f"{attempts:,}".replace(",", "."), icon="book"),
            dict(
                label="Tỷ lệ đạt",
                value=percent(ratio(quiz.passed.sum(), attempts)),
                icon="check",
                note="Điểm đạt từ 70%",
            ),
            dict(
                label="Tỷ lệ câu trả lời đúng",
                value=percent(ratio(quiz.correct_answers.sum(), quiz.question_count.sum())),
                icon="chart",
                note="Tổng câu đúng / tổng câu hỏi",
            ),
            dict(
                label="Đề thi có lượt làm", value=f"{len(quiz):,}".replace(",", "."), icon="users"
            ),
        ]
    )
    with card():
        card_title("Đề thi có tỷ lệ trượt cao", "Xếp theo tỷ lệ trượt, sau đó theo số lượt làm bài")
        first, second, third = st.columns([1, 1, 1.5])
        with first:
            top = st.selectbox("Số đề hiển thị", [5, 10, 15], index=1, key="quiz_top")
        with second:
            minimum = st.number_input(
                "Lượt thi tối thiểu",
                min_value=1,
                max_value=max(1, int(quiz.attempts.max())) if not quiz.empty else 1,
                value=1,
                key="quiz_min",
            )
        with third:
            search = st.text_input("Tìm đề thi", placeholder="Mã đề hoặc tên đề", key="quiz_search")
        filtered = quiz.loc[quiz.attempts >= minimum].copy()
        if search:
            filtered = filtered.loc[
                filtered.quiz_id.astype(str).str.contains(search, regex=False)
                | filtered.quiz_title.str.contains(search, case=False, regex=False)
            ]
        filtered["fail_pct"] = 100 - filtered.pass_pct
        difficult = (
            filtered.sort_values(
                ["fail_pct", "attempts", "quiz_id"], ascending=[False, False, True]
            )
            .head(top)
            .copy()
        )
        difficult["label"] = difficult.quiz_id.map(lambda value: f"Đề {value}")
        if difficult.empty:
            empty("Không có đề thi phù hợp với điều kiện đã chọn.")
        else:
            plot(ranked_chart(difficult, "fail_pct", "label", "percent"), "exam_ranking")
    with st.expander("Chi tiết đề thi và xuất dữ liệu"):
        table(
            filtered,
            "de_thi",
            {
                "quiz_id": "Mã đề",
                "quiz_title": "Tên đề",
                "category": "Lĩnh vực",
                "attempts": "Lượt thi",
                "pass_pct": "Đạt (%)",
                "fail_pct": "Trượt (%)",
                "avg_score_pct": "Điểm trung bình (%)",
                "duration_score_corr": "Tương quan thời lượng–điểm",
                "passed": "Lượt đạt",
                "correct_answers": "Câu đúng",
                "question_count": "Tổng câu hỏi",
            },
        )
    with st.expander("Phân tích thời gian học và điểm quiz"):
        st.caption(
            "Tính trên ghi danh có cả bài học và quiz trong kỳ. Tương quan không chứng minh quan hệ nhân quả; không xác định khi điểm hoặc thời lượng không biến thiên."
        )
        if st.checkbox("Tải phân tích tương quan", key="study_detail"):
            try:
                study = load_detail(manifest["run_id"], "study", start, end, selected_categories)
                table(
                    study,
                    "tuong_quan_hoc_diem",
                    {
                        "course_id": "Mã khóa",
                        "title": "Khóa học",
                        "enrollments": "Ghi danh",
                        "correlation": "Tương quan",
                    },
                )
            except Exception:
                logging.exception("Study drilldown failed")
                st.error("Chưa thể tải phân tích chi tiết. Hãy làm mới dữ liệu rồi thử lại.")

elif page == "Thị trường":
    cities = data["cities"]
    metrics(
        [
            dict(label="Doanh thu ròng", value=short_number(net, 2) + " ₫", icon="money"),
            dict(
                label="Giao dịch thanh toán", value=f"{payments:,}".replace(",", "."), icon="chart"
            ),
            dict(label="Thành phố có giao dịch", value=str(len(cities)), icon="users"),
            dict(
                label="Tỷ trọng thành phố dẫn đầu",
                value=percent(ratio(cities.net_vnd.iloc[0], net)) if not cities.empty else "—",
                icon="chart",
                note=str(cities.city.iloc[0]) if not cities.empty else "Chưa có giao dịch",
            ),
        ]
    )
    left, right = st.columns([1.3, 1], gap="medium")
    with left, card():
        card_title("Giảng viên theo doanh thu", "Doanh thu ròng · VND")
        limit = st.selectbox("Số giảng viên", [5, 10, 15], index=1, key="instructor_limit")
        instructors = data["instructors"].head(limit).copy()
        instructors["label"] = (
            instructors.apply(
                lambda row: f"{row.full_name} · #{row.instructor_id}"
                if instructors.full_name.duplicated(keep=False).loc[row.name]
                else row.full_name,
                axis=1,
            )
            if not instructors.empty
            else pd.Series(dtype=str)
        )
        if instructors.empty:
            empty()
        else:
            plot(ranked_chart(instructors, "net_vnd", "label"), "market_instructors")
    with right, card():
        card_title("Doanh thu theo địa lý", "Thành phố của học viên tại ngày thanh toán")
        if cities.empty:
            empty()
        else:
            plot(ranked_chart(cities, "net_vnd", "city", height=365), "market_cities")
    with st.expander("Chi tiết giảng viên và địa lý"):
        table(
            data["instructors"],
            "giang_vien",
            {
                "instructor_id": "Mã giảng viên",
                "full_name": "Giảng viên",
                "net_vnd": "Doanh thu ròng (₫)",
                "payments": "Giao dịch",
            },
        )
        table(
            cities,
            "dia_ly",
            {"city": "Thành phố", "net_vnd": "Doanh thu ròng (₫)", "payments": "Giao dịch"},
        )
    with st.expander("Học viên chuyển vùng và tăng trưởng theo năm"):
        st.caption(
            "Địa lý theo lịch sử tại ngày thanh toán. YoY chỉ tính khi chọn đủ hai năm lịch liền kề và doanh thu năm trước khác 0."
        )
        if st.checkbox("Tải lịch sử học viên chuyển vùng", key="mover_detail"):
            try:
                movers = load_detail(
                    manifest["run_id"], "movers", start, end, selected_categories
                ).copy()
                previous_year = movers.groupby("city")["year"].shift()
                previous_revenue = movers.groupby("city")["net_vnd"].shift()
                movers["yoy_pct"] = [
                    (row.net_vnd / previous_revenue[index] - 1) * 100
                    if previous_year[index] == int(row.year) - 1
                    and previous_revenue[index] != 0
                    and start <= date(int(row.year) - 1, 1, 1)
                    and end >= date(int(row.year), 12, 31)
                    else None
                    for index, row in movers.iterrows()
                ]
                table(
                    movers,
                    "hoc_vien_chuyen_vung",
                    {
                        "city": "Thành phố",
                        "year": "Năm",
                        "net_vnd": "Doanh thu ròng (₫)",
                        "yoy_pct": "YoY (%)",
                    },
                )
            except Exception:
                logging.exception("Mover drilldown failed")
                st.error("Chưa thể tải lịch sử địa lý. Hãy làm mới dữ liệu rồi thử lại.")

else:
    errors = data["quarantine"]
    total_errors = int(errors["Tổng"].sum()) if not errors.empty else 0
    open_errors = int(errors["Chưa xử lý"].sum()) if not errors.empty else 0
    metrics(
        [
            dict(
                label="Kiểm tra chất lượng",
                value=str(manifest["quality_checks"]),
                icon="check",
                note="Bản Gold đã công bố",
            ),
            dict(
                label="Lỗi chưa giải quyết",
                value=str(open_errors),
                icon="book",
                note="Bản ghi trong quarantine",
            ),
            dict(
                label="Lỗi đã giải quyết",
                value=str(total_errors - open_errors),
                icon="check",
                note="Đã có phiên bản hợp lệ thay thế",
            ),
            dict(
                label="Lần nạp gần nhất",
                value=f"{manifest['seconds']:.2f}".replace(".", ",") + " giây",
                icon="clock",
                note="Incremental rỗng" if manifest.get("gold_reused") else manifest["mode"],
            ),
        ]
    )
    quality_tab, ops_tab = st.tabs(["Chất lượng dữ liệu", "Nhật ký vận hành"])
    with quality_tab, card():
        card_title("Trạng thái bản dữ liệu", tag="Đã đối soát")
        st.markdown(
            '<div class="quality-summary"><b>'
            + (
                "Không có bản ghi cần xử lý"
                if not open_errors
                else str(open_errors) + " bản ghi đang cần xử lý"
            )
            + "</b><p>Kiểm tra kiểu dữ liệu, khóa tham chiếu, lịch sử học viên, tiền và đối soát tổng trước khi công bố.</p></div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Kiểm tra gần nhất "
            + pd.to_datetime(manifest["quality_checked_at"], utc=True).strftime(
                "%d/%m/%Y %H:%M UTC"
            )
            + ". Lần nạp rỗng giữ kết quả kiểm tra của bản Gold trước đó."
        )
        if not errors.empty:
            table(errors, "tong_hop_cach_ly")
            with st.expander("Các lỗi phát hiện gần nhất"):
                table(data["recent_errors"], "loi_gan_nhat")
    with ops_tab, card():
        card_title("Lịch sử nạp dữ liệu", "10 lần chạy gần nhất")
        table(data["runs"], "nhat_ky_pipeline")
        with st.expander("Thông tin bản công bố"):
            st.json(
                {
                    key: manifest.get(key)
                    for key in [
                        "run_id",
                        "mode",
                        "started_at",
                        "finished_at",
                        "seconds",
                        "peak_rss_mib",
                        "fact_actions",
                        "extracted",
                        "rejected",
                    ]
                }
            )
        st.caption(
            "Nạp incremental xử lý thay đổi trên toàn nguồn, không phụ thuộc bộ lọc phân tích."
        )
        if st.button("Nạp dữ liệu tăng dần", type="primary"):
            try:
                with st.spinner("Đang nạp, kiểm tra và công bố dữ liệu…"):
                    result = subprocess.run(
                        [sys.executable, "cli.py", "pipeline", "--mode", "incremental"],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        timeout=1200,
                    )
                if result.returncode:
                    st.error(
                        "Lần nạp chưa hoàn tất. Bản Gold đã công bố được giữ lại. Kiểm tra nhật ký pipeline để xử lý."
                    )
                else:
                    st.cache_data.clear()
                    st.rerun()
            except subprocess.TimeoutExpired:
                st.error(
                    "Lần nạp quá thời gian chờ. Kiểm tra trạng thái pipeline trước khi chạy lại."
                )

with st.expander("Nguồn dữ liệu và định nghĩa chỉ số"):
    st.caption(
        "Nguồn: ClickHouse Gold. Dữ liệu giả lập phục vụ học tập và trình diễn. Các truy vấn phân tích dùng cùng bản công bố và cùng bộ lọc."
    )
    st.markdown(
        "**Doanh thu ròng** = giá trị gốc − giảm giá − hoàn tiền, tính theo ngày thanh toán. **Tỷ lệ hoàn thành** = lượt đã hoàn thành / lượt ghi danh trong cohort. **Điểm đạt** từ 70% số câu hỏi."
    )
    st.caption(
        "Năm mới nhất kết thúc tại ngày ghi danh cuối cùng có trong nguồn. Chọn Toàn kỳ hoặc Tùy chọn để xem những sự kiện học tập xảy ra sau ngày này."
    )
    if prior:
        st.caption(
            f"So sánh cùng kỳ: {prior['start']:%d/%m/%Y} — {prior['end']:%d/%m/%Y}. Chênh lệch tỷ lệ tính bằng điểm phần trăm. Hai năm có thể khác số ngày do năm nhuận."
        )
    else:
        st.caption(
            "Không hiển thị chênh lệch khi phạm vi chọn không có kỳ so sánh phù hợp trong dữ liệu 2022–2024."
        )
    source = dict(
        run_id=manifest["run_id"],
        published_at=manifest["finished_at"],
        start=str(start),
        end=str(end),
        categories=selected_categories,
        comparison=prior,
        synthetic=True,
        timezone="UTC",
        currency="VND",
    )
    st.download_button(
        "Tải thông tin nguồn",
        json.dumps(source, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
        file_name="nguon_du_lieu.json",
        mime="application/json",
    )
st.markdown(
    '<div class="footer"><span>Learning Warehouse · Dữ liệu giả lập</span><span>Bản dữ liệu '
    + escape(manifest["run_id"][:8])
    + " · VND / UTC</span></div>",
    unsafe_allow_html=True,
)

