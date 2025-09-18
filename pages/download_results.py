"""
결과 다운로드 페이지 모듈
"""
import streamlit as st
import pandas as pd
from utils.common import get_sample_results_data

def render():
    """결과 다운로드 페이지 렌더링"""
    st.title("📥 Download Results")
    st.markdown("---")
    
    st.markdown("""
    ## Processing History
    
    완료된 파이프라인 작업의 결과를 다운로드할 수 있습니다.
    """)
    
    # 가상의 처리 결과 데이터
    results_data = get_sample_results_data()
    
    # 필터링 옵션
    st.markdown("### 🔍 Filter Results")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            options=['All', 'Completed', 'Processing', 'Failed'],
            index=0
        )
    
    with col2:
        pipeline_filter = st.selectbox(
            "Pipeline Filter",
            options=['All'] + list(results_data['Pipeline'].unique()),
            index=0
        )
    
    with col3:
        date_filter = st.date_input(
            "From Date",
            value=results_data['Date'].min(),
            help="Show results from this date onwards"
        )
    
    # 필터 적용
    filtered_data = results_data.copy()
    if status_filter != 'All':
        filtered_data = filtered_data[filtered_data['Status'] == status_filter]
    if pipeline_filter != 'All':
        filtered_data = filtered_data[filtered_data['Pipeline'] == pipeline_filter]
    
    filtered_data = filtered_data[filtered_data['Date'] >= pd.Timestamp(date_filter)]
    
    # 통계 정보 표시
    st.markdown("### 📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Jobs", len(filtered_data))
    
    with col2:
        completed_jobs = len(filtered_data[filtered_data['Status'] == 'Completed'])
        st.metric("Completed", completed_jobs)
    
    with col3:
        if completed_jobs > 0:
            avg_accuracy = filtered_data[filtered_data['Status'] == 'Completed']['Accuracy'].mean()
            st.metric("Avg Accuracy", f"{avg_accuracy:.1%}")
        else:
            st.metric("Avg Accuracy", "N/A")
    
    with col4:
        total_files = filtered_data['Files'].sum()
        st.metric("Total Files", total_files)
    
    # 결과 테이블
    st.markdown("### 📋 Results Table")
    
    # 상태별 색상 표시를 위한 스타일링
    def style_status(val):
        if val == 'Completed':
            return 'background-color: #d4edda; color: #155724'
        elif val == 'Processing':
            return 'background-color: #fff3cd; color: #856404'
        elif val == 'Failed':
            return 'background-color: #f8d7da; color: #721c24'
        return ''
    
    styled_data = filtered_data.style.applymap(style_status, subset=['Status'])
    st.dataframe(styled_data, use_container_width=True)
    
    # 다운로드 섹션
    st.markdown("### 💾 Download Options")
    
    completed_jobs = filtered_data[filtered_data['Status'] == 'Completed']
    
    if len(completed_jobs) > 0:
        # 개별 작업 선택 다운로드
        st.markdown("#### 📄 Individual Job Download")
        selected_job = st.selectbox(
            "Select Job to Download",
            options=completed_jobs['Job ID'].tolist(),
            help="Choose a specific job to download its results"
        )
        
        # 선택된 작업 정보 표시
        selected_job_info = completed_jobs[completed_jobs['Job ID'] == selected_job].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **📋 Job Details:**
            - Job ID: {selected_job_info['Job ID']}
            - Pipeline: {selected_job_info['Pipeline']}
            - Date: {selected_job_info['Date'].strftime('%Y-%m-%d')}
            - Files Processed: {selected_job_info['Files']}
            """)
        
        with col2:
            st.markdown(f"""
            **📊 Results:**
            - Status: {selected_job_info['Status']}
            - Accuracy: {selected_job_info['Accuracy']:.1%}
            - Quality Score: {(selected_job_info['Accuracy'] * 100):.0f}/100
            """)
        
        # 다운로드 버튼들
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📄 Download Report (PDF)",
                data=f"Analysis report for {selected_job}",
                file_name=f"report_{selected_job}.pdf",
                mime="application/pdf",
                help="Download detailed analysis report"
            )
        
        with col2:
            st.download_button(
                label="📊 Download Data (CSV)",
                data=filtered_data.to_csv(index=False),
                file_name=f"data_{selected_job}.csv",
                mime="text/csv",
                help="Download raw analysis data"
            )
        
        with col3:
            st.download_button(
                label="🖼️ Download Images (ZIP)",
                data=f"Processed images for {selected_job}",
                file_name=f"images_{selected_job}.zip",
                mime="application/zip",
                help="Download processed images and visualizations"
            )
        
        # 일괄 다운로드
        st.markdown("#### 📦 Batch Download")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Download All Completed Results", use_container_width=True):
                st.success("🎉 Preparing batch download... This may take a few moments.")
                st.info("💡 You will receive an email notification when the download is ready.")
        
        with col2:
            st.download_button(
                label="📋 Export Table (Excel)",
                data=filtered_data.to_csv(index=False),  # 실제로는 Excel 형식으로 변환
                file_name="pipeline_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # 자동 다운로드 설정
        st.markdown("#### ⚙️ Download Preferences")
        
        with st.expander("🔧 Auto-download Settings"):
            auto_download = st.checkbox("Enable automatic download for completed jobs")
            email_notifications = st.checkbox("Send email notifications", value=True)
            download_format = st.selectbox(
                "Default download format",
                options=['PDF + Data', 'PDF Only', 'Data Only', 'All Files']
            )
            
            if st.button("💾 Save Preferences"):
                st.success("✅ Preferences saved successfully!")
    
    else:
        st.info("ℹ️ No completed jobs available for download with current filters.")
        st.markdown("**💡 Suggestions:**")
        st.markdown("- Try changing the filter settings")
        st.markdown("- Check if any pipelines are currently running")
        st.markdown("- Run a new pipeline from the 'Run Pipeline' menu")
