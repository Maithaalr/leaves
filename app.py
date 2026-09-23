import streamlit as st
import pandas as pd
import plotly.express as px


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="تحليل الإجازات والأذونات",
    page_icon="",
    layout="wide"
)

st.title(" لوحة تحليل الإجازات والأذونات")
st.caption("تحليل بيانات الإجازات والأذونات للدوائر الحكومية")


# =========================================================
# CLEAN TEXT
# =========================================================
def clean_text_series(series):

    return (
        series
        .astype("string")
        .str.replace("\u202a", "", regex=False)
        .str.replace("\u202b", "", regex=False)
        .str.replace("\u202c", "", regex=False)
        .str.replace("\u200e", "", regex=False)
        .str.replace("\u200f", "", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )


# =========================================================
# DATE CONVERSION
# =========================================================
def convert_date_column(series):
    """
    تحويل التواريخ مثل:
    25/08/2025
    25-08-2025
    Excel datetime
    Excel serial date

    مع تنظيف رموز RTL/LTR المخفية.
    """

    # إذا Excel قرأ العمود كتاريخ فعلي
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    # تحويل إلى نص
    cleaned = series.astype("string")

    # =====================================================
    # إزالة الرموز المخفية
    # بدون Regex لتجنب مشكلة PyArrow
    # =====================================================
    hidden_chars = [
        "\u200e",  # LTR mark
        "\u200f",  # RTL mark
        "\u202a",  # LTR embedding
        "\u202b",  # RTL embedding
        "\u202c",  # pop directional formatting
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
        "\ufeff",
    ]

    for char in hidden_chars:
        cleaned = cleaned.str.replace(
            char,
            "",
            regex=False
        )

    cleaned = (
        cleaned
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )

    # القيم الفارغة
    cleaned = cleaned.replace(
        [
            "",
            "nan",
            "NaN",
            "None",
            "<NA>",
            "NaT"
        ],
        pd.NA
    )

    # النتيجة النهائية
    result = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]"
    )

    # =====================================================
    # 1. DD/MM/YYYY
    # مثال: 25/08/2025
    # =====================================================
    mask_slash = cleaned.str.match(
        r"^[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}$",
        na=False
    )

    if mask_slash.any():
        result.loc[mask_slash] = pd.to_datetime(
            cleaned.loc[mask_slash],
            format="%d/%m/%Y",
            errors="coerce"
        )

    # =====================================================
    # 2. DD-MM-YYYY
    # =====================================================
    mask_dash = (
        result.isna()
        & cleaned.str.match(
            r"^[0-9]{1,2}-[0-9]{1,2}-[0-9]{4}$",
            na=False
        )
    )

    if mask_dash.any():
        result.loc[mask_dash] = pd.to_datetime(
            cleaned.loc[mask_dash],
            format="%d-%m-%Y",
            errors="coerce"
        )

    # =====================================================
    # 3. Excel Serial Date
    # مثال: 45894
    # =====================================================
    numeric_dates = pd.to_numeric(
        cleaned,
        errors="coerce"
    )

    excel_mask = (
        result.isna()
        & numeric_dates.notna()
        & numeric_dates.between(20000, 80000)
    )

    if excel_mask.any():
        result.loc[excel_mask] = pd.to_datetime(
            numeric_dates.loc[excel_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )

    # =====================================================
    # 4. محاولة أخيرة لأي صيغة أخرى
    # =====================================================
    remaining = (
        result.isna()
        & cleaned.notna()
    )

    if remaining.any():

        try:
            fallback = pd.to_datetime(
                cleaned.loc[remaining],
                format="mixed",
                dayfirst=True,
                errors="coerce"
            )

        except (TypeError, ValueError):
            fallback = pd.to_datetime(
                cleaned.loc[remaining],
                dayfirst=True,
                errors="coerce"
            )

        result.loc[remaining] = fallback

    return result
# =========================================================
# CLEAN DATA
# =========================================================
def clean_data(df):

    # تنظيف أسماء الأعمدة
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\u202a", "", regex=False)
        .str.replace("\u202b", "", regex=False)
        .str.replace("\u202c", "", regex=False)
        .str.replace("\u200e", "", regex=False)
        .str.replace("\u200f", "", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    # الحقول النصية
    text_columns = [
        "اسم الدائرة",
        "رقم الموظف",
        "اسم الموظف",
        "الوحدة التنظيمية",
        "اسم الاجازة او الاذن"
    ]

    for col in text_columns:

        if col in df.columns:

            df[col] = clean_text_series(
                df[col]
            )

            df[col] = df[col].replace(
                [
                    "",
                    "nan",
                    "NaN",
                    "None",
                    "<NA>"
                ],
                pd.NA
            )

    # من تاريخ
    if "من تاريخ" in df.columns:

        df["من تاريخ"] = convert_date_column(
            df["من تاريخ"]
        )

        df["السنة"] = (
            df["من تاريخ"]
            .dt.year
            .astype("Int64")
        )

    # إلى تاريخ
    if "الى تاريخ" in df.columns:

        df["الى تاريخ"] = convert_date_column(
            df["الى تاريخ"]
        )

    # عدد الأيام
    if "عدد الايام" in df.columns:

        df["عدد الايام"] = pd.to_numeric(
            df["عدد الايام"],
            errors="coerce"
        )

    # عدد الساعات
    if "عدد الساعات" in df.columns:

        df["عدد الساعات"] = pd.to_numeric(
            df["عدد الساعات"],
            errors="coerce"
        )

    return df


# =========================================================
# UNIQUE EMPLOYEES
# =========================================================
def unique_employees(df):

    if "رقم الموظف" not in df.columns:
        return 0

    return (
        df["رقم الموظف"]
        .dropna()
        .nunique()
    )


# =========================================================
# LEAVE ANALYSIS
# =========================================================
def leave_analysis(df):

    if "اسم الاجازة او الاذن" not in df.columns:
        return pd.DataFrame()

    data = df[
        df["اسم الاجازة او الاذن"].notna()
    ].copy()

    if data.empty:
        return pd.DataFrame()

    result = (
        data["اسم الاجازة او الاذن"]
        .value_counts()
        .reset_index()
    )

    result.columns = [
        "اسم الإجازة أو الإذن",
        "عدد مرات التكرار"
    ]

    total = result[
        "عدد مرات التكرار"
    ].sum()

    if total > 0:

        result["النسبة"] = (
            result["عدد مرات التكرار"]
            / total
            * 100
        ).round(2)

    else:

        result["النسبة"] = 0

    result["النسبة %"] = (
        result["النسبة"]
        .apply(
            lambda x: f"{x:.2f}%"
        )
    )

    return result


# =========================================================
# YEAR ANALYSIS
# =========================================================
def year_analysis(df):

    years = [
        2023,
        2024,
        2025,
        2026
    ]

    if "السنة" not in df.columns:

        return pd.DataFrame({
            "السنة": [
                str(x) for x in years
            ],
            "عدد الإجازات والأذونات": [
                0,
                0,
                0,
                0
            ]
        })

    result = (
        df[
            df["السنة"].isin(years)
        ]
        .groupby("السنة")
        .size()
        .reindex(
            years,
            fill_value=0
        )
        .reset_index(
            name="عدد الإجازات والأذونات"
        )
    )

    result["السنة"] = (
        result["السنة"]
        .astype(int)
        .astype(str)
    )

    return result


# =========================================================
# DAYS STATISTICS
# =========================================================
def days_statistics(df):

    default = {
        "mean": 0,
        "median": 0,
        "min": 0,
        "max": 0,
        "sum": 0
    }

    if "عدد الايام" not in df.columns:
        return default

    days = (
        df["عدد الايام"]
        .dropna()
    )

    if days.empty:
        return default

    return {
        "mean": days.mean(),
        "median": days.median(),
        "min": days.min(),
        "max": days.max(),
        "sum": days.sum()
    }


# =========================================================
# HOURS STATISTICS
# =========================================================
def hours_statistics(df):

    default = {
        "mean": 0,
        "min": 0,
        "max": 0,
        "sum": 0
    }

    if "عدد الساعات" not in df.columns:
        return default

    hours = (
        df["عدد الساعات"]
        .dropna()
    )

    if hours.empty:
        return default

    positive_hours = hours[
        hours > 0
    ]

    total_hours = hours.sum()

    if positive_hours.empty:

        return {
            "mean": 0,
            "min": 0,
            "max": 0,
            "sum": total_hours
        }

    return {
        "mean": positive_hours.mean(),
        "min": positive_hours.min(),
        "max": positive_hours.max(),
        "sum": total_hours
    }


# =========================================================
# PERMISSION / USAGE ANALYSIS
# =========================================================
def permission_mask(df):
    """اعتبار أي سجل يحتوي اسمه على كلمة إذن/اذن كسجل إذن."""
    if "اسم الاجازة او الاذن" not in df.columns:
        return pd.Series(False, index=df.index)

    names = clean_text_series(df["اسم الاجازة او الاذن"]).fillna("")
    return names.str.contains(r"(?:إذن|اذن)", regex=True, na=False)


def permission_data(df):
    return df.loc[permission_mask(df)].copy()


def usage_kpis(df):
    """مؤشرات استخدام الأذونات فقط."""
    data = permission_data(df)
    employees = unique_employees(data)
    requests = len(data)

    if "عدد الساعات" in data.columns:
        hours = pd.to_numeric(data["عدد الساعات"], errors="coerce").fillna(0)
        total_hours = hours.sum()
        positive = hours[hours > 0]
        avg_request_hours = positive.mean() if not positive.empty else 0
    else:
        total_hours = 0
        avg_request_hours = 0

    hours_per_employee = total_hours / employees if employees else 0
    requests_per_employee = requests / employees if employees else 0

    return {
        "employees": employees,
        "requests": requests,
        "total_hours": total_hours,
        "hours_per_employee": hours_per_employee,
        "requests_per_employee": requests_per_employee,
        "avg_request_hours": avg_request_hours,
    }


def display_permission_kpis(df):
    st.subheader("⏱️ مؤشرات استخدام الأذونات")
    k = usage_kpis(df)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("👥 مستخدمو الأذونات", f"{k['employees']:,}")
    c2.metric("📝 عدد الأذونات", f"{k['requests']:,}")
    c3.metric("⏰ إجمالي ساعات الأذونات", f"{k['total_hours']:,.2f}")
    c4.metric("👤 متوسط الساعات لكل مستخدم", f"{k['hours_per_employee']:,.2f}")
    c5.metric("🔁متوسط الاضن لكل مستخدم", f"{k['requests_per_employee']:,.2f}")


def permission_type_analysis(df):
    data = permission_data(df)
    if data.empty:
        return pd.DataFrame()

    result = (
        data.groupby("اسم الاجازة او الاذن", dropna=False)
        .agg(
            عدد_المرات=("رقم الموظف", "size"),
            عدد_الموظفين=("رقم الموظف", "nunique"),
            إجمالي_الساعات=("عدد الساعات", "sum"),
        )
        .reset_index()
    )
    result.columns = ["نوع الإذن", "عدد المرات", "عدد الموظفين", "إجمالي الساعات"]
    result["متوسط الساعات للإذن"] = (
        result["إجمالي الساعات"] / result["عدد المرات"].replace(0, pd.NA)
    ).fillna(0).round(2)
    total = result["إجمالي الساعات"].sum()
    result["النسبة من الساعات %"] = (
        result["إجمالي الساعات"] / total * 100 if total else 0
    ).round(2)
    return result.sort_values("إجمالي الساعات", ascending=False)


def display_permission_types(df, chart_key):
    st.subheader("🪪 تحليل أنواع الأذونات")
    analysis = permission_type_analysis(df)
    if analysis.empty:
        st.info("لا توجد سجلات أذونات في البيانات المختارة.")
        return

    col1, col2 = st.columns([1.15, 1.35])
    with col1:
        st.dataframe(analysis, use_container_width=True, hide_index=True)
    with col2:
        chart = analysis.sort_values("إجمالي الساعات", ascending=True)
        fig = px.bar(
            chart,
            x="إجمالي الساعات",
            y="نوع الإذن",
            orientation="h",
            text="إجمالي الساعات",
            hover_data=["عدد المرات", "عدد الموظفين", "متوسط الساعات للإذن", "النسبة من الساعات %"],
        )
        fig.update_traces(texttemplate="%{text:,.1f}", textposition="outside")
        fig.update_layout(xaxis_title="إجمالي الساعات", yaxis_title="", height=max(350, len(chart) * 55))
        st.plotly_chart(fig, use_container_width=True, key=chart_key)


def build_department_usage_summary(df):
    data = permission_data(df)
    if data.empty:
        return pd.DataFrame()

    result = (
        data.dropna(subset=["اسم الدائرة"])
        .groupby("اسم الدائرة")
        .agg(
            عدد_المستخدمين=("رقم الموظف", "nunique"),
            عدد_الأذونات=("رقم الموظف", "size"),
            إجمالي_الساعات=("عدد الساعات", "sum"),
        )
        .reset_index()
    )
    result["ساعة لكل مستخدم"] = (
        result["إجمالي_الساعات"] / result["عدد_المستخدمين"].replace(0, pd.NA)
    ).fillna(0).round(2)
    result["إذن لكل مستخدم"] = (
        result["عدد_الأذونات"] / result["عدد_المستخدمين"].replace(0, pd.NA)
    ).fillna(0).round(2)
    total_hours = result["إجمالي_الساعات"].sum()
    result["نسبة الساعات %"] = (
        result["إجمالي_الساعات"] / total_hours * 100 if total_hours else 0
    ).round(2)
    result = result.rename(columns={
        "عدد_المستخدمين": "عدد المستخدمين",
        "عدد_الأذونات": "عدد الأذونات",
        "إجمالي_الساعات": "إجمالي الساعات",
    })
    return result.sort_values("إجمالي الساعات", ascending=False)


def display_department_usage(df):
    st.subheader("🏢 مقارنة استخدام الأذونات بين الدوائر")
    summary = build_department_usage_summary(df)
    if summary.empty:
        st.info("لا توجد بيانات أذونات كافية للمقارنة بين الدوائر.")
        return

    st.dataframe(summary, use_container_width=True, hide_index=True)

    metric = st.radio(
        "اختر مؤشر المقارنة",
        ["إجمالي الساعات", "ساعة لكل مستخدم", "عدد الأذونات", "إذن لكل مستخدم"],
        horizontal=True,
        key="department_usage_metric",
    )
    chart = summary.sort_values(metric, ascending=True)
    fig = px.bar(chart, x=metric, y="اسم الدائرة", orientation="h", text=metric)
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=metric, yaxis_title="", height=max(450, len(chart) * 38))
    st.plotly_chart(fig, use_container_width=True, key="department_usage_bar")

    st.subheader("🔎 حجم الجهة مقابل كثافة الاستخدام")
    fig_scatter = px.scatter(
        summary,
        x="عدد المستخدمين",
        y="ساعة لكل مستخدم",
        size="إجمالي الساعات",
        hover_name="اسم الدائرة",
        hover_data=["عدد الأذونات", "إذن لكل مستخدم", "نسبة الساعات %"],
        size_max=55,
    )
    fig_scatter.update_layout(
        xaxis_title="عدد مستخدمي الأذونات",
        yaxis_title="متوسط ساعات الأذونات لكل مستخدم",
    )
    st.plotly_chart(fig_scatter, use_container_width=True, key="department_usage_scatter")

# =========================================================
# KPIs
# =========================================================
def display_kpis(df):

    employees = unique_employees(df)

    total_records = len(df)

    days = days_statistics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "👥 عدد الموظفين",
        f"{employees:,}"
    )

    col2.metric(
        "📋 إجمالي الإجازات والأذونات",
        f"{total_records:,}"
    )

    col3.metric(
        "📅 متوسط عدد الأيام",
        f"{days['mean']:,.2f}"
    )

    col4.metric(
        "⬇️ أقل عدد أيام",
        f"{days['min']:,.2f}"
    )

    col5.metric(
        "⬆️ أعلى عدد أيام",
        f"{days['max']:,.2f}"
    )


# =========================================================
# LEAVE TYPES
# =========================================================
def display_leave_types(
    df,
    chart_key
):

    analysis = leave_analysis(df)

    if analysis.empty:

        st.info(
            "لا توجد بيانات إجازات أو أذونات."
        )

        return

    col1, col2 = st.columns(
        [1, 1.4]
    )

    with col1:

        st.subheader(
            "📋 أنواع الإجازات والأذونات"
        )

        display_table = analysis[
            [
                "اسم الإجازة أو الإذن",
                "عدد مرات التكرار",
                "النسبة %"
            ]
        ]

        st.dataframe(
            display_table,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        st.subheader(
            "📊 عدد مرات التكرار"
        )

        chart_data = (
            analysis
            .sort_values(
                "عدد مرات التكرار",
                ascending=True
            )
        )

        fig = px.bar(
            chart_data,
            x="عدد مرات التكرار",
            y="اسم الإجازة أو الإذن",
            orientation="h",
            text="عدد مرات التكرار"
        )

        fig.update_layout(
            xaxis_title="عدد مرات التكرار",
            yaxis_title="",
            height=max(
                400,
                len(chart_data) * 38
            )
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=chart_key
        )


# =========================================================
# YEARS
# =========================================================
def display_years(
    df,
    chart_key
):

    st.subheader(
        "📆 توزيع الإجازات والأذونات حسب السنة"
    )

    analysis = year_analysis(df)

    col1, col2 = st.columns(
        [1.4, 1]
    )

    with col1:

        fig = px.bar(
            analysis,
            x="السنة",
            y="عدد الإجازات والأذونات",
            text="عدد الإجازات والأذونات"
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            xaxis_title="السنة",
            yaxis_title="عدد الإجازات والأذونات"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=chart_key
        )

    with col2:

        st.dataframe(
            analysis,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# DAYS DISPLAY
# =========================================================
def display_days_statistics(df):

    st.subheader(
        "📅 إحصائيات عدد الأيام"
    )

    stats = days_statistics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "متوسط الأيام",
        f"{stats['mean']:,.2f}"
    )

    col2.metric(
        "الوسيط",
        f"{stats['median']:,.2f}"
    )

    col3.metric(
        "أقل عدد أيام",
        f"{stats['min']:,.2f}"
    )

    col4.metric(
        "أعلى عدد أيام",
        f"{stats['max']:,.2f}"
    )

    col5.metric(
        "إجمالي الأيام",
        f"{stats['sum']:,.2f}"
    )


# =========================================================
# HOURS DISPLAY
# =========================================================
def display_hours_statistics(df):

    st.subheader(
        "⏰ إحصائيات عدد الساعات"
    )

    stats = hours_statistics(df)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "متوسط الساعات",
        f"{stats['mean']:,.2f}"
    )

    col2.metric(
        "أقل عدد ساعات",
        f"{stats['min']:,.2f}"
    )

    col3.metric(
        "أعلى عدد ساعات",
        f"{stats['max']:,.2f}"
    )

    col4.metric(
        "إجمالي الساعات",
        f"{stats['sum']:,.2f}"
    )


# =========================================================
# FILE UPLOADER
# =========================================================
uploaded_file = st.file_uploader(
    "📂 ارفعي ملف بيانات الإجازات والأذونات",
    type=[
        "xlsx",
        "xls",
        "csv"
    ]
)


# =========================================================
# MAIN
# =========================================================
if uploaded_file is None:

    st.info(
        "⬆️ ارفعي ملف Excel أو CSV لبدء التحليل."
    )

    st.stop()


# =========================================================
# READ FILE
# =========================================================
try:

    if uploaded_file.name.lower().endswith(
        ".csv"
    ):

        df = pd.read_csv(
            uploaded_file
        )

    else:

        df = pd.read_excel(
            uploaded_file
        )

except Exception as e:

    st.error(
        "حدث خطأ أثناء قراءة الملف."
    )

    st.exception(e)

    st.stop()


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================
df.columns = (
    df.columns
    .astype(str)
    .str.replace("\u202a", "", regex=False)
    .str.replace("\u202b", "", regex=False)
    .str.replace("\u202c", "", regex=False)
    .str.replace("\u200e", "", regex=False)
    .str.replace("\u200f", "", regex=False)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)


# =========================================================
# REQUIRED COLUMNS
# =========================================================
required_columns = [
    "اسم الدائرة",
    "رقم الموظف",
    "اسم الموظف",
    "اسم الاجازة او الاذن",
    "من تاريخ",
    "عدد الايام",
    "عدد الساعات"
]


missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]


if missing_columns:

    st.error(
        "الملف لا يحتوي على بعض الحقول المطلوبة:"
    )

    for col in missing_columns:

        st.write(
            f"• {col}"
        )

    st.write(
        "الأعمدة الموجودة في الملف:"
    )

    st.write(
        list(df.columns)
    )

    st.stop()


# =========================================================
# CLEAN DATA
# =========================================================
try:

    df = clean_data(
        df
    )

except Exception as e:

    st.error(
        "حدث خطأ أثناء تنظيف البيانات."
    )

    st.exception(e)

    st.stop()


df = df.dropna(
    how="all"
)


# =========================================================
# SUCCESS
# =========================================================
st.success(
    f"تم تحميل الملف بنجاح — "
    f"عدد السجلات: {len(df):,}"
)


# =========================================================
# DATE CHECK
# =========================================================
invalid_from_dates = (
    df["من تاريخ"]
    .isna()
    .sum()
)


if "الى تاريخ" in df.columns:

    invalid_to_dates = (
        df["الى تاريخ"]
        .isna()
        .sum()
    )

else:

    invalid_to_dates = 0


if (
    invalid_from_dates > 0
    or invalid_to_dates > 0
):

    with st.expander(
        "⚠️ ملاحظات على التواريخ"
    ):

        st.write(
            f"عدد القيم الفارغة أو غير القابلة للتحويل "
            f"في «من تاريخ»: "
            f"{invalid_from_dates:,}"
        )

        if "الى تاريخ" in df.columns:

            st.write(
                f"عدد القيم الفارغة أو غير القابلة للتحويل "
                f"في «الى تاريخ»: "
                f"{invalid_to_dates:,}"
            )


# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(
    [
        "📊 الإحصائيات العامة",
        "🏢 تحليل حسب الدائرة",
        "⏱️ تحليل الأذونات"
    ]
)


# =========================================================
# TAB 1
# =========================================================
with tab1:

    st.header(
        "الإحصائيات العامة لجميع الدوائر"
    )

    # KPIs
    display_kpis(
        df
    )

    st.divider()

    # =====================================================
    # DEPARTMENT SUMMARY
    # =====================================================
    st.subheader(
        "🏢 ملخص الدوائر"
    )

    department_summary = (
        df
        .dropna(
            subset=[
                "اسم الدائرة"
            ]
        )
        .groupby(
            "اسم الدائرة"
        )
        .agg(
            عدد_الموظفين=(
                "رقم الموظف",
                "nunique"
            ),
            عدد_الإجازات_والأذونات=(
                "رقم الموظف",
                "size"
            )
        )
        .reset_index()
    )


    department_summary.columns = [
        "اسم الدائرة",
        "عدد الموظفين",
        "عدد الإجازات والأذونات"
    ]


    department_summary = (
        department_summary
        .sort_values(
            "عدد الإجازات والأذونات",
            ascending=False
        )
    )


    col1, col2 = st.columns(
        [1, 1.4]
    )


    with col1:

        st.dataframe(
            department_summary,
            use_container_width=True,
            hide_index=True
        )


    with col2:

        department_chart_data = (
            department_summary
            .sort_values(
                "عدد الإجازات والأذونات",
                ascending=True
            )
        )


        fig_departments = px.bar(
            department_chart_data,
            x="عدد الإجازات والأذونات",
            y="اسم الدائرة",
            orientation="h",
            text="عدد الإجازات والأذونات"
        )


        fig_departments.update_layout(
            xaxis_title="عدد الإجازات والأذونات",
            yaxis_title="",
            height=max(
                400,
                len(
                    department_summary
                ) * 38
            )
        )


        fig_departments.update_traces(
            textposition="outside"
        )


        st.plotly_chart(
            fig_departments,
            use_container_width=True,
            key="general_departments_chart"
        )


    st.divider()

    # مؤشرات الأذونات
    display_permission_kpis(df)

    st.divider()

    # =====================================================
    # LEAVE TYPES
    # =====================================================
    display_leave_types(
        df,
        chart_key="general_leave_types_chart"
    )


    st.divider()


    # =====================================================
    # YEARS
    # =====================================================
    display_years(
        df,
        chart_key="general_year_chart"
    )


    st.divider()


    # =====================================================
    # DAYS
    # =====================================================
    display_days_statistics(
        df
    )


    st.divider()


    # =====================================================
    # HOURS
    # =====================================================
    display_hours_statistics(
        df
    )


# =========================================================
# TAB 2
# =========================================================
with tab2:

    st.header(
        "🏢 تحليل حسب الدائرة"
    )


    departments = sorted(
        df[
            "اسم الدائرة"
        ]
        .dropna()
        .unique()
        .tolist()
    )


    if not departments:

        st.warning(
            "لا توجد دوائر متاحة في البيانات."
        )

    else:

        col_filter1, col_filter2 = (
            st.columns(2)
        )


        # =================================================
        # DEPARTMENT FILTER
        # =================================================
        with col_filter1:

            selected_department = (
                st.selectbox(
                    "اختر الدائرة",
                    departments,
                    key="department_filter"
                )
            )


        department_df = df[
            df["اسم الدائرة"]
            == selected_department
        ].copy()


        # =================================================
        # YEARS AVAILABLE
        # =================================================
        available_years = (
            department_df[
                "السنة"
            ]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )


        available_years = sorted(
            [
                year
                for year
                in available_years
                if year
                in [
                    2023,
                    2024,
                    2025,
                    2026
                ]
            ]
        )


        year_options = (
            ["كل السنوات"]
            + available_years
        )


        # =================================================
        # YEAR FILTER
        # =================================================
        with col_filter2:

            selected_year = (
                st.selectbox(
                    "اختر السنة",
                    year_options,
                    key="year_filter"
                )
            )


        # =================================================
        # FILTER DATA
        # =================================================
        if (
            selected_year
            != "كل السنوات"
        ):

            filtered_df = (
                department_df[
                    department_df[
                        "السنة"
                    ]
                    == int(
                        selected_year
                    )
                ]
                .copy()
            )

        else:

            filtered_df = (
                department_df.copy()
            )


        # =================================================
        # FILTER INFO
        # =================================================
        if (
            selected_year
            == "كل السنوات"
        ):

            st.info(
                f"الدائرة المختارة: "
                f"{selected_department} "
                f"| جميع السنوات"
            )

        else:

            st.info(
                f"الدائرة المختارة: "
                f"{selected_department} "
                f"| السنة: "
                f"{selected_year}"
            )


        # =================================================
        # NO DATA
        # =================================================
        if filtered_df.empty:

            st.warning(
                "لا توجد بيانات مطابقة للفلاتر المختارة."
            )

        else:

            # KPIs
            display_kpis(
                filtered_df
            )


            st.divider()

            display_permission_kpis(filtered_df)

            st.divider()

            display_permission_types(
                filtered_df,
                chart_key="department_permission_types_chart"
            )

            st.divider()

            # LEAVE TYPES
            display_leave_types(
                filtered_df,
                chart_key="department_leave_types_chart"
            )


            st.divider()


            # YEARS
            if (
                selected_year
                == "كل السنوات"
            ):

                display_years(
                    filtered_df,
                    chart_key="department_year_chart"
                )

                st.divider()


            # DAYS
            display_days_statistics(
                filtered_df
            )


            st.divider()


            # HOURS
            display_hours_statistics(
                filtered_df
            )


            st.divider()


            # =================================================
            # DETAILS
            # =================================================
            with st.expander(
                "🔎 عرض البيانات التفصيلية"
            ):

                columns_to_show = [
                    "تسلسل",
                    "اسم الدائرة",
                    "رقم الموظف",
                    "اسم الموظف",
                    "الوحدة التنظيمية",
                    "اسم الاجازة او الاذن",
                    "من تاريخ",
                    "وقت البداية",
                    "الى تاريخ",
                    "وقت النهاية",
                    "عدد الايام",
                    "عدد الساعات"
                ]


                existing_columns = [
                    col
                    for col
                    in columns_to_show
                    if col
                    in filtered_df.columns
                ]


                detail_df = (
                    filtered_df[
                        existing_columns
                    ]
                    .copy()
                )


                # =============================================
                # DISPLAY FROM DATE
                # =============================================
                if (
                    "من تاريخ"
                    in detail_df.columns
                ):

                    detail_df[
                        "من تاريخ"
                    ] = (
                        detail_df[
                            "من تاريخ"
                        ]
                        .dt.strftime(
                            "%d/%m/%Y"
                        )
                    )


                # =============================================
                # DISPLAY TO DATE
                # =============================================
                if (
                    "الى تاريخ"
                    in detail_df.columns
                ):

                    detail_df[
                        "الى تاريخ"
                    ] = (
                        detail_df[
                            "الى تاريخ"
                        ]
                        .dt.strftime(
                            "%d/%m/%Y"
                        )
                    )


                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True
                )

# =========================================================
# TAB 3 - PERMISSIONS ANALYSIS
# =========================================================
with tab3:
    st.header("⏱️ التحليل المتقدم للأذونات")
    st.caption("يركز هذا القسم على سجلات الأذونات فقط، ويقارن حجم الاستخدام وكثافته بين الدوائر.")

    display_permission_kpis(df)
    st.divider()
    display_permission_types(df, chart_key="general_permission_types_chart")
    st.divider()
    display_department_usage(df)

    st.divider()
    st.subheader("📆 اتجاه ساعات الأذونات حسب السنة")
    p_df = permission_data(df)
    if not p_df.empty and "السنة" in p_df.columns:
        trend = (
            p_df.dropna(subset=["السنة"])
            .groupby("السنة")
            .agg(
                عدد_الأذونات=("رقم الموظف", "size"),
                إجمالي_الساعات=("عدد الساعات", "sum"),
                عدد_المستخدمين=("رقم الموظف", "nunique"),
            )
            .reset_index()
            .sort_values("السنة")
        )
        trend["السنة"] = trend["السنة"].astype(int).astype(str)
        trend["ساعة لكل مستخدم"] = (
            trend["إجمالي_الساعات"] / trend["عدد_المستخدمين"].replace(0, pd.NA)
        ).fillna(0).round(2)

        c1, c2 = st.columns([1.4, 1])
        with c1:
            fig = px.line(
                trend,
                x="السنة",
                y="إجمالي_الساعات",
                markers=True,
                text="إجمالي_الساعات",
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(xaxis_title="السنة", yaxis_title="إجمالي ساعات الأذونات")
            st.plotly_chart(fig, use_container_width=True, key="permission_year_trend")
        with c2:
            st.dataframe(trend, use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد بيانات سنوات كافية لتحليل اتجاه الأذونات.")
