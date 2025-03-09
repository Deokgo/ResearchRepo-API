from config import Session
from sqlalchemy import text

import numpy as np

def get_data_for_performance_overview(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT 
                    program_id, year 
                FROM get_data_for_performance_overview_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT 
                    college_id, program_id, year 
                FROM get_data_for_performance_overview(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_research_type_bar_plot(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT 
                    program_id, research_type 
                FROM get_data_for_research_type_bar_plot_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT 
                    college_id, program_id, research_type 
                FROM get_data_for_research_type_bar_plot(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_research_status_bar_plot(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT 
                    program_id, status 
                FROM get_data_for_research_status_bar_plot_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT 
                    college_id, program_id, status 
                FROM get_data_for_research_status_bar_plot(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_scopus_section(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT * FROM get_data_for_scopus_section_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT * FROM get_data_for_scopus_section(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_jounal_section(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT * FROM get_data_for_jounal_section_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT * FROM get_data_for_jounal_section(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_sdg(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        # Convert numpy arrays to lists
        selected_colleges = selected_colleges.tolist() if hasattr(selected_colleges, 'tolist') else selected_colleges
        selected_programs = selected_programs.tolist() if hasattr(selected_programs, 'tolist') else selected_programs
        selected_status = selected_status.tolist() if hasattr(selected_status, 'tolist') else selected_status
        selected_terms = selected_terms.tolist() if hasattr(selected_terms, 'tolist') else selected_terms
        
        # Check if selected_colleges is None (not using == for numpy arrays)
        if selected_colleges is None:
            query = text("""
                SELECT
                    program_id, sdg 
                FROM get_data_for_sdg_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT
                    college_id, program_id, sdg 
                FROM get_data_for_sdg(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_modal_contents(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT * FROM get_data_for_modal_contents_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT * FROM get_data_for_modal_contents(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()

def get_data_for_text_displays(selected_colleges=None, selected_programs=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        if selected_colleges == None:
            query = text("""
                SELECT * FROM get_data_for_text_displays_bycollege(:selected_programs, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_programs': selected_programs,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })
        else:
            query = text("""
                SELECT * FROM get_data_for_text_displays(:selected_colleges, :selected_status, :selected_years, :selected_terms)
            """)

            result = session.execute(query, {
                'selected_colleges': selected_colleges,
                'selected_status': selected_status,
                'selected_years': selected_years,
                'selected_terms': selected_terms
            })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()