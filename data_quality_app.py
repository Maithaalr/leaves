import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================================
# إعداد الصفحة
# =========================================================
st.set_page_config(
    page_title="تحليل الإجازات والأذونات",
    page_icon="📊",
    layout="wide"
)

st.title("📊 لوحة تحليل الإجازات والأذونات")
st.caption("تحليل بيانات الإجازات والأذونات للدوائر الحكومية")


# =========================================================
# دوال مساعدة
# =========================================================
def clean_data(df):
    """تنظيف وتجهيز البيانات للتحليل"""

    # إزالة المسافات من أسماء الأعمدة
    df.columns = df.columns.astype(str).str.strip()

    # تنظيف النصوص
    text_columns = [
        "اسم الدائرة",
        "رقم الموظف",
        "اسم الموظف",
        "الوحدة التنظيمية",
        "اسم الاجازة او الاذن"
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # تحويل التواريخ
    if "من تاريخ" in df.columns:
        df["من تاريخ"] = pd.to_datetime(
            df["من تاريخ"],
            errors="coerce",
            dayfirst=True
        )

        df["السنة"] = df["من تاريخ"].dt.year

    if "الى تاريخ" in df.columns:
        df["الى تاريخ"] = pd.to_datetime(
            df["الى تاريخ"],
            errors="coerce",
            dayfirst=True
        )

    # تحويل عدد الأيام والساعات إلى أرقام
    if "عدد الايام" in df.columns:
        df["عدد الايام"] = pd.to_numeric(
            df["عدد الايام"],
            errors="coerce"
        )

    if "عدد الساعات" in df.columns:
        df["عدد الساعات"] = pd.to_numeric(
            df["عدد الساعات"],
            errors="coerce"
        )

    return df


def unique_employees(df):
    """عدد الموظفين بدون تكرار"""
    if "رقم الموظف" not in df.columns:
        return 0

    return df["رقم الموظف"].dropna().nunique()


def leave_analysis(df):
    """تحليل أنواع الإجازات والأذونات"""

    if "اسم الاجازة او الاذن" not in df.columns:
        return pd.DataFrame()

    data = df[
        df["اسم الاجازة او الاذن"].notna()
        & (df["اسم الاجازة او الاذن"].str.strip() != "")
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

    total = result["عدد مرات التكرار"].sum()

    result["النسبة"] = (
        result["عدد مرات التكرار"] / total * 100
    ).round(2)

    result["النسبة %"] = result["النسبة"].apply(
        lambda x: f"{x:.2f}%"
    )

    return result


def year_analysis(df):
    """تحليل البيانات حسب السنة"""

    years = [2023, 2024, 2025, 2026]

    if "السنة" not in df.columns:
        return pd.DataFrame({
            "السنة": years,
            "عدد الإجازات والأذونات": [0, 0, 0, 0]
        })

    result = (
        df[df["السنة"].isin(years)]
        .groupby("السنة")
        .size()
        .reindex(years, fill_value=0)
        .reset_index(name="عدد الإجازات والأذونات")
    )

    result["السنة"] = result["السنة"].astype(int).astype(str)

    return result


def days_statistics(df):
    """إحصائيات عدد الأيام"""

    if "عدد الايام" not in df.columns:
        return {
            "mean": 0,
            "median": 0,
            "min": 0,
            "max": 0,
            "sum": 0
        }

    days = df["عدد الايام"].dropna()

    if len(days) == 0:
        return {
            "mean": 0,
            "median": 0,
            "min": 0,
            "max": 0,
            "sum": 0
        }

    return {
        "mean": days.mean(),
        "median": days.median(),
        "min": days.min(),
        "max": days.max(),
        "sum": days.sum()
    }


def hours_statistics(df):
    """إحصائيات عدد الساعات"""

    if "عدد الساعات" not in df.columns:
        return {
            "mean": 0,
            "min": 0,
            "max": 0,
            "sum": 0
        }

    hours = df["عدد الساعات"].dropna()

    # نتجاهل الصفر في المتوسط والأقل والأعلى
    positive_hours = hours[hours > 0]

    if len(hours) == 0:
        return {
            "mean": 0,
            "min": 0,
            "max": 0,
            "sum": 0
        }

    if len(positive_hours) == 0:
        return {
            "mean": 0,
            "min": 0,
            "max": 0,
            "sum": hours.sum()
        }

    return {
        "mean": positive_hours.mean(),
        "min": positive_hours.min(),
        "max": positive_hours.max(),
        "sum": hours.sum()
    }


def display_kpis(df):
    """عرض المؤشرات الرئيسية"""

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
        f"{days['mean']:.2f}"
    )

    col4.metric(
        "⬇️ أقل عدد أيام",
        f"{days['min']:,.2f}"
    )

    col5.metric(
        "⬆️ أعلى عدد أيام",
        f"{days['max']:,.2f}"
    )


def display_leave_types(df):
    """عرض تحليل أنواع الإجازات"""

    analysis = leave_analysis(df)

    if analysis.empty:
        st.info("لا توجد بيانات إجازات أو أذونات.")
        return

    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("📋 أنواع الإجازات والأذونات")

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
        st.subheader("📊 عدد مرات التكرار")

        chart_data = analysis.sort_values(
            "عدد مرات التكرار",
            ascending=True
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
            height=max(400, len(chart_data) * 35)
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


def display_years(df):
    """عرض التحليل حسب السنوات"""

    st.subheader("📆 توزيع الإجازات والأذونات حسب السنة")

    analysis = year_analysis(df)

    col1, col2 = st.columns([1.4, 1])

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
            use_container_width=True
        )

    with col2:
        st.dataframe(
            analysis,
            use_container_width=True,
            hide_index=True
        )


def display_days_statistics(df):
    """عرض إحصائيات الأيام"""

    st.subheader("📅 إحصائيات عدد الأيام")

    stats = days_statistics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "متوسط الأيام",
        f"{stats['mean']:.2f}"
    )

    col2.metric(
        "الوسيط",
        f"{stats['median']:.2f}"
    )

    col3.metric(
        "أقل عدد أيام",
        f"{stats['min']:.2f}"
    )

    col4.metric(
        "أعلى عدد أيام",
        f"{stats['max']:.2f}"
    )

    col5.metric(
        "إجمالي الأيام",
        f"{stats['sum']:,.2f}"
    )


def display_hours_statistics(df):
    """عرض إحصائيات الساعات"""

    st.subheader("⏰ إحصائيات عدد الساعات")

    stats = hours_statistics(df)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "متوسط الساعات",
        f"{stats['mean']:.2f}"
    )

    col2.metric(
        "أقل عدد ساعات",
        f"{stats['min']:.2f}"
    )

    col3.metric(
        "أعلى عدد ساعات",
        f"{stats['max']:.2f}"
    )

    col4.metric(
        "إجمالي الساعات",
        f"{stats['sum']:,.2f}"
    )


# =========================================================
# رفع الملف
# =========================================================
uploaded_file = st.file_uploader(
    "📂 ارفعي ملف بيانات الإجازات والأذونات",
    type=["xlsx", "xls", "csv"]
)


if uploaded_file is not None:

    try:

        # =================================================
        # قراءة الملف
        # =================================================
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # تنظيف أسماء الأعمدة
        df.columns = df.columns.astype(str).str.strip()

        # =================================================
        # التحقق من الحقول
        # =================================================
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
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:

            st.error(
                "الملف لا يحتوي على بعض الحقول المطلوبة:"
            )

            for col in missing_columns:
                st.write(f"• {col}")

            st.write("الأعمدة الموجودة في الملف:")
            st.write(list(df.columns))

            st.stop()

        # تنظيف البيانات
        df = clean_data(df)

        # إزالة الصفوف الفارغة بالكامل
        df = df.dropna(how="all")

        st.success(
            f"تم تحميل الملف بنجاح — عدد السجلات: {len(df):,}"
        )

        # =================================================
        # التابات
        # =================================================
        tab1, tab2 = st.tabs(
            [
                "📊 الإحصائيات العامة",
                "🏢 تحليل حسب الدائرة"
            ]
        )

        # =================================================
        # TAB 1
        # =================================================
        with tab1:

            st.header("الإحصائيات العامة لجميع الدوائر")

            # KPI
            display_kpis(df)

            st.divider()

            # =============================================
            # تحليل الدوائر
            # =============================================
            st.subheader("🏢 ملخص الدوائر")

            department_summary = (
                df.groupby("اسم الدائرة")
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

            department_summary = department_summary.sort_values(
                "عدد الإجازات والأذونات",
                ascending=False
            )

            col1, col2 = st.columns([1, 1.4])

            with col1:

                st.dataframe(
                    department_summary,
                    use_container_width=True,
                    hide_index=True
                )

            with col2:

                fig_departments = px.bar(
                    department_summary.sort_values(
                        "عدد الإجازات والأذونات",
                        ascending=True
                    ),
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
                        len(department_summary) * 35
                    )
                )

                fig_departments.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig_departments,
                    use_container_width=True
                )

            st.divider()

            # =============================================
            # أنواع الإجازات
            # =============================================
            display_leave_types(df)

            st.divider()

            # =============================================
            # السنوات
            # =============================================
            display_years(df)

            st.divider()

            # =============================================
            # الأيام
            # =============================================
            display_days_statistics(df)

            st.divider()

            # =============================================
            # الساعات
            # =============================================
            display_hours_statistics(df)

        # =================================================
        # TAB 2
        # =================================================
        with tab2:

            st.header("🏢 تحليل حسب الدائرة")

            departments = sorted(
                df["اسم الدائرة"]
                .dropna()
                .unique()
                .tolist()
            )

            col_filter1, col_filter2 = st.columns(2)

            with col_filter1:

                selected_department = st.selectbox(
                    "اختر الدائرة",
                    departments
                )

            department_df = df[
                df["اسم الدائرة"]
                == selected_department
            ].copy()

            # =============================================
            # فلتر السنة
            # =============================================
            available_years = (
                department_df["السنة"]
                .dropna()
                .astype(int)
                .unique()
                .tolist()
            )

            available_years = sorted(
                [
                    year for year in available_years
                    if year in [2023, 2024, 2025, 2026]
                ]
            )

            year_options = ["كل السنوات"] + available_years

            with col_filter2:

                selected_year = st.selectbox(
                    "اختر السنة",
                    year_options
                )

            # تطبيق فلتر السنة
            if selected_year != "كل السنوات":
                filtered_df = department_df[
                    department_df["السنة"]
                    == selected_year
                ].copy()
            else:
                filtered_df = department_df.copy()

            st.info(
                f"الدائرة المختارة: {selected_department}"
                +
                (
                    f" | السنة: {selected_year}"
                    if selected_year != "كل السنوات"
                    else " | جميع السنوات"
                )
            )

            # =============================================
            # KPI
            # =============================================
            display_kpis(filtered_df)

            st.divider()

            # =============================================
            # أنواع الإجازات
            # =============================================
            display_leave_types(filtered_df)

            st.divider()

            # =============================================
            # السنوات
            # إذا كان كل السنوات
            # =============================================
            if selected_year == "كل السنوات":
                display_years(filtered_df)

                st.divider()

            # =============================================
            # الأيام
            # =============================================
            display_days_statistics(filtered_df)

            st.divider()

            # =============================================
            # الساعات
            # =============================================
            display_hours_statistics(filtered_df)

            st.divider()

            # =============================================
            # البيانات التفصيلية
            # =============================================
            with st.expander(
                "🔎 عرض البيانات التفصيلية"
            ):

                columns_to_show = [
                    "اسم الدائرة",
                    "رقم الموظف",
                    "اسم الموظف",
                    "الوحدة التنظيمية",
                    "اسم الاجازة او الاذن",
                    "من تاريخ",
                    "الى تاريخ",
                    "عدد الايام",
                    "عدد الساعات"
                ]

                existing_columns = [
                    col for col in columns_to_show
                    if col in filtered_df.columns
                ]

                st.dataframe(
                    filtered_df[existing_columns],
                    use_container_width=True,
                    hide_index=True
                )

    except Exception as e:

        st.error(
            "حدث خطأ أثناء قراءة أو تحليل الملف."
        )

        st.exception(e)


else:

    st.info(
        "⬆️ ارفعي ملف Excel أو CSV لبدء التحليل."
    )
