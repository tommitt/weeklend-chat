import altair as alt
import pandas as pd
import requests
import streamlit as st

from interface.backend import FASTAPI_URL
from interface.utils.schemas import DashboardOutput


def ui() -> None:
    st.title("Weeklend 📊")

    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start date")
    end_date = col2.date_input("End date")

    if st.button("Get stats", use_container_width=True):
        response = requests.post(
            f"{FASTAPI_URL}/dashboard",
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        )
        st.session_state.dashboard_out = DashboardOutput(**response.json())

    if "dashboard_out" in st.session_state:
        st.header(f"Overview")
        st.dataframe(
            pd.DataFrame(
                {
                    "": ["Users", "Messages", "Avg messages x user"],
                    "Value": [
                        st.session_state.dashboard_out.users,
                        st.session_state.dashboard_out.conversations,
                        st.session_state.dashboard_out.avg_messages_per_user,
                    ],
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

        st.header(f"Users")
        show_donut_chart_with_df(
            categories=["New", "Recurring"],
            values=[
                st.session_state.dashboard_out.users_new,
                st.session_state.dashboard_out.users_recurring,
            ],
            category_label="User type",
            value_label="# Users",
            container=st.container(),
        )

        st.header(f"Conversations")
        col_messages, _, col_answers = st.columns([10, 1, 10])

        col_messages.subheader("Received messages")
        show_donut_chart_with_df(
            categories=[
                "Answered",
                "Unanswered",
                "Failed to elaborate",
            ],
            values=[
                st.session_state.dashboard_out.conversations_answered,
                st.session_state.dashboard_out.conversations_unanswered,
                st.session_state.dashboard_out.conversations_failed,
            ],
            category_label="Response type",
            value_label="# Messages",
            container=col_messages,
        )

        col_answers.subheader("Answered messages")
        show_donut_chart_with_df(
            categories=[
                "AI recommendation",
                "AI conversational",
                "Welcome template",
                "Other template",
                "Blocked",
            ],
            values=[
                st.session_state.dashboard_out.conversations_answered_ai,
                st.session_state.dashboard_out.conversations_answered_conversational,
                st.session_state.dashboard_out.conversations_answered_welcome_template,
                st.session_state.dashboard_out.conversations_answered_other_template,
                st.session_state.dashboard_out.conversations_answered_blocked,
            ],
            category_label="Answer type",
            value_label="# Answers",
            container=col_answers,
        )

    else:
        st.caption("No stats to show")


def show_donut_chart_with_df(
    categories: list[str],
    values: list[int],
    category_label: str,
    value_label: str,
    container,
) -> None:
    df = pd.DataFrame({category_label: categories, value_label: values})
    chart = (
        alt.Chart(data=df)
        .mark_arc(innerRadius=50)
        .encode(
            color=alt.Color(field=category_label, type="nominal"),
            theta=alt.Theta(field=value_label, type="quantitative"),
        )
    )

    total_row = pd.DataFrame(
        {category_label: ["Total"], value_label: [df[value_label].sum()]}
    )
    df = pd.concat([df, total_row])

    with container:
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, hide_index=True, use_container_width=True)
