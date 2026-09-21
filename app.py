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
# دالة تنظيف النصوص
# =========================================================
def clean_text_series(series):
    """
    تنظيف النصوص من المسافات والعلامات المخفية
    """

    return (
        series
        .astype("string")
        .str.replace("\u202a", "", regex=False)
        .str.replace("\u202b", "", regex=False)
        .str.replace("\u202c", "", regex=False)
        .str.replace("\u200e", "", regex=False)
        .str.replace("\u200f", "", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )


# =========================================================
# دالة تحويل التاريخ
# =========================================================
def convert_date_column(series):
    """
    تنظيف وتحويل التاريخ إلى datetime
    يدعم قيم مثل:
    22/04/2024
    ‭22/04/2024‬
    """

    # إذا Excel قرأ التاريخ أصلاً كـ datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(
            series,
            errors="coerce"
        )

    # تنظيف النص
    cleaned = clean_text_series(series)

    # استبدال القيم الفارغة
    cleaned = cleaned.replace(
        ["", "nan", "NaN", "None", "<NA>"],
        pd.NA
    )

    # تحويل التاريخ
    converted = pd.to_datetime(
        cleaned,
        errors="coerce",
        dayfirst=True
    )

    return converted


# =========================================================
# تنظيف وتجهيز البيانات
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

    # -----------------------------------------------------
    # الحقول النصية
    # -----------------------------------------------------
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
                ["", "nan", "NaN", "None", "<NA>"],
                pd.NA
            )

    # -----------------------------------------------------
    # تحويل من تاريخ
    # -----------------------------------------------------
    if "من تاريخ" in df.columns:

        df["من تاريخ"] = convert_date_column(
            df["من تاريخ"]
        )

        # استخراج السنة
        df["السنة"] = (
            df["من تاريخ"]
            .dt.year
            .astype("Int64")
        )

    # -----------------------------------------------------
    # تحويل إلى تاريخ
    # -----------------------------------------------------
    if "الى تاريخ" in df.columns:

        df["الى تاريخ"] = convert_date_column(
            df["الى تاريخ"]
        )

    # -----------------------------------------------------
    # عدد الأيام
    # -----------------------------------------------------
    if "عدد الايام" in df.columns:

        df["عدد الايام"] = pd.to_numeric(
            df["عدد الايام"],
            errors="coerce"
        )

    # -----------------------------------------------------
    # عدد الساعات
    # -----------------------------------------------------
    if "عدد الساعات" in df.columns:

        df["عدد الساعات"] = pd.to_numeric(
            df["عدد الساعات"],
            errors="coerce"
        )

    return df


# =========================================================
# عدد الموظفين بدون تكرار
# =========================================================
def unique_employees(df):

    if "رقم الموظف" not in df.columns:
        return 0

    employees = df["رقم الموظف"].dropna()

    return employees.nunique()


# =========================================================
# تحليل أنواع الإجازات والأذونات
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
# تحليل السنوات
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
                0, 0, 0, 0
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
# إحصائيات الأيام
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
# إحصائيات الساعات
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

    # نستخدم القيم الأكبر من صفر
    # للمتوسط والأقل والأعلى
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
# عرض المؤشرات الرئيسية
# =========================================================
def display_kpis(df):

    employees = unique_employees(df)

    total_records = len(df)

    days = days_statistics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "👥 عدد الموظفين",
            f"{employees:,}"
        )

    with col2:

        st.metric(
            "📋 إجمالي الإجازات والأذونات",
            f"{total_records:,}"
        )

    with col3:

        st.metric(
            "📅 متوسط عدد الأيام",
            f"{days['mean']:,.2f}"
        )

    with col4:

        st.metric(
            "⬇️ أقل عدد أيام",
            f"{days['min']:,.2f}"
        )

    with col5:

        st.metric(
            "⬆️ أعلى عدد أيام",
            f"{days['max']:,.2f}"
        )


# =========================================================
# عرض أنواع الإجازات والأذونات
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

    # -----------------------------------------------------
    # الجدول
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # الرسم
    # -----------------------------------------------------
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
# عرض تحليل السنوات
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

    # -----------------------------------------------------
    # الرسم
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # الجدول
    # -----------------------------------------------------
    with col2:

        st.dataframe(
            analysis,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# عرض إحصائيات الأيام
# =========================================================
def display_days_statistics(df):

    st.subheader(
        "📅 إحصائيات عدد الأيام"
    )

    stats = days_statistics(df)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "متوسط الأيام",
            f"{stats['mean']:,.2f}"
        )

    with col2:

        st.metric(
            "الوسيط",
            f"{stats['median']:,.2f}"
        )

    with col3:

        st.metric(
            "أقل عدد أيام",
            f"{stats['min']:,.2f}"
        )

    with col4:

        st.metric(
            "أعلى عدد أيام",
            f"{stats['max']:,.2f}"
        )

    with col5:

        st.metric(
            "إجمالي الأيام",
            f"{stats['sum']:,.2f}"
        )


# =========================================================
# عرض إحصائيات الساعات
# =========================================================
def display_hours_statistics(df):

    st.subheader(
        "⏰ إحصائيات عدد الساعات"
    )

    stats = hours_statistics(df)

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "متوسط الساعات",
            f"{stats['mean']:,.2f}"
        )

    with col2:

        st.metric(
            "أقل عدد ساعات",
            f"{stats['min']:,.2f}"
        )

    with col3:

        st.metric(
            "أعلى عدد ساعات",
            f"{stats['max']:,.2f}"
        )

    with col4:

        st.metric(
            "إجمالي الساعات",
            f"{stats['sum']:,.2f}"
        )


# =========================================================
# رفع الملف
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
# عند رفع الملف
# =========================================================
if uploaded_file is not None:

    try:

        # =================================================
        # قراءة الملف
        # =================================================
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

        # =================================================
        # تنظيف أسماء الأعمدة قبل التحقق
        # =================================================
        df.columns = (
            df.columns
            .astype(str)
            .str.replace(
                "\u202a",
                "",
                regex=False
            )
            .str.replace(
                "\u202b",
                "",
                regex=False
            )
            .str.replace(
                "\u202c",
                "",
                regex=False
            )
            .str.replace(
                "\u200e",
                "",
                regex=False
            )
            .str.replace(
                "\u200f",
                "",
                regex=False
            )
            .str.replace(
                "\ufeff",
                "",
                regex=False
            )
            .str.strip()
        )

        # =================================================
        # الحقول المطلوبة
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
            col
            for col in required_columns
            if col not in df.columns
        ]

        # =================================================
        # إذا في حقول ناقصة
        # =================================================
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

        # =================================================
        # تنظيف البيانات
        # =================================================
        df = clean_data(df)

        # إزالة الصفوف الفارغة بالكامل
        df = df.dropna(
            how="all"
        )

        # =================================================
        # معلومات التحميل
        # =================================================
        st.success(
            f"تم تحميل الملف بنجاح — "
            f"عدد السجلات: {len(df):,}"
        )

        # =================================================
        # التحقق من التواريخ
        # =================================================
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
                    f"عدد القيم غير القابلة للتحويل "
                    f"في «من تاريخ»: "
                    f"{invalid_from_dates:,}"
                )

                if "الى تاريخ" in df.columns:

                    st.write(
                        f"عدد القيم غير القابلة للتحويل "
                        f"في «الى تاريخ»: "
                        f"{invalid_to_dates:,}"
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

            st.header(
                "الإحصائيات العامة لجميع الدوائر"
            )

            # -------------------------------------------------
            # المؤشرات الرئيسية
            # -------------------------------------------------
            display_kpis(df)

            st.divider()

            # -------------------------------------------------
            # ملخص الدوائر
            # -------------------------------------------------
            st.subheader(
                "🏢 ملخص الدوائر"
            )

            department_summary = (
                df
                .dropna(
                    subset=["اسم الدائرة"]
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

            # -------------------------------------------------
            # جدول الدوائر
            # -------------------------------------------------
            with col1:

                st.dataframe(
                    department_summary,
                    use_container_width=True,
                    hide_index=True
                )

            # -------------------------------------------------
            # رسم الدوائر
            # -------------------------------------------------
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
                    xaxis_title=(
                        "عدد الإجازات والأذونات"
                    ),
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

            # -------------------------------------------------
            # أنواع الإجازات
            # -------------------------------------------------
            display_leave_types(
                df,
                chart_key=(
                    "general_leave_types_chart"
                )
            )

            st.divider()

            # -------------------------------------------------
            # السنوات
            # -------------------------------------------------
            display_years(
                df,
                chart_key=(
                    "general_year_chart"
                )
            )

            st.divider()

            # -------------------------------------------------
            # الأيام
            # -------------------------------------------------
            display_days_statistics(
                df
            )

            st.divider()

            # -------------------------------------------------
            # الساعات
            # -------------------------------------------------
            display_hours_statistics(
                df
            )

        # =================================================
        # TAB 2
        # =================================================
        with tab2:

            st.header(
                "🏢 تحليل حسب الدائرة"
            )

            # =================================================
            # قائمة الدوائر
            # =================================================
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

                st.stop()

            # =================================================
            # الفلاتر
            # =================================================
            col_filter1, col_filter2 = (
                st.columns(2)
            )

            # -------------------------------------------------
            # فلتر الدائرة
            # -------------------------------------------------
            with col_filter1:

                selected_department = (
                    st.selectbox(
                        "اختر الدائرة",
                        departments,
                        key=(
                            "department_filter"
                        )
                    )
                )

            # -------------------------------------------------
            # بيانات الدائرة
            # -------------------------------------------------
            department_df = df[
                df["اسم الدائرة"]
                == selected_department
            ].copy()

            # =================================================
            # السنوات المتوفرة
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

            # -------------------------------------------------
            # فلتر السنة
            # -------------------------------------------------
            with col_filter2:

                selected_year = (
                    st.selectbox(
                        "اختر السنة",
                        year_options,
                        key=(
                            "year_filter"
                        )
                    )
                )

            # =================================================
            # تطبيق فلتر السنة
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
            # عرض الاختيار
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
            # التحقق من وجود بيانات
            # =================================================
            if filtered_df.empty:

                st.warning(
                    "لا توجد بيانات مطابقة "
                    "للفلاتر المختارة."
                )

            else:

                # -------------------------------------------------
                # المؤشرات
                # -------------------------------------------------
                display_kpis(
                    filtered_df
                )

                st.divider()

                # -------------------------------------------------
                # أنواع الإجازات
                # -------------------------------------------------
                display_leave_types(
                    filtered_df,
                    chart_key=(
                        "department_leave_types_chart"
                    )
                )

                st.divider()

                # -------------------------------------------------
                # السنوات
                # -------------------------------------------------
                if (
                    selected_year
                    == "كل السنوات"
                ):

                    display_years(
                        filtered_df,
                        chart_key=(
                            "department_year_chart"
                        )
                    )

                    st.divider()

                # -------------------------------------------------
                # الأيام
                # -------------------------------------------------
                display_days_statistics(
                    filtered_df
                )

                st.divider()

                # -------------------------------------------------
                # الساعات
                # -------------------------------------------------
                display_hours_statistics(
                    filtered_df
                )

                st.divider()

                # -------------------------------------------------
                # البيانات التفصيلية
                # -------------------------------------------------
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
                    def convert_date_column(series):
                        """
                        تحويل التاريخ من DD/MM/YYYY إلى datetime
                        مثال:
                        22/04/2024
                        """

    # إذا Excel قارئ العمود أصلاً كتاريخ
                        if pd.api.types.is_datetime64_any_dtype(series):
                            return pd.to_datetime(
                                series,
                                errors="coerce"
                            )

                        # تحويل إلى نص
                        cleaned = series.astype("string")

                        # تنظيف جميع الرموز المخفية
                        cleaned = (
                            cleaned
                            .str.replace("\u202a", "", regex=False)
                            .str.replace("\u202b", "", regex=False)
                            .str.replace("\u202c", "", regex=False)
                            .str.replace("\u200e", "", regex=False)
                            .str.replace("\u200f", "", regex=False)
                            .str.replace("\ufeff", "", regex=False)
                            .str.replace("\xa0", "", regex=False)
                            .str.strip()
                        )

                        # الاحتفاظ فقط بالأرقام و /
                        cleaned = cleaned.str.replace(
                            r"[^\d/]",
                            "",
                            regex=True
                        )

                        # تحويل التاريخ بالصيغة المحددة
                        converted = pd.to_datetime(
                            cleaned,
                            format="%d/%m/%Y",
                            errors="coerce"
                        )

                        return converted

# =====================================================
  # معالجة الأخطاء
 # =====================================================

except Exception as e:

    st.error(


    "حدث خطأ أثناء قراءة أو تحليل الملف."

     )


    st.exception(e)

# =========================================================
# قبل رفع الملف
# =========================================================
else:

    st.info(
        "⬆️ ارفعي ملف Excel أو CSV لبدء التحليل."
    )
