"""OpsOrchestrator — Master coordinator that runs all agents concurrently via asyncio.gather."""

import asyncio
from datetime import datetime

from opscore.agents.email_agent import EmailAgent
from opscore.agents.calendar_agent import CalendarAgent
from opscore.agents.report_agent import ReportAgent
from opscore.services import gemini_service


class OpsOrchestrator:
    """Master orchestrator that coordinates all agents for the Fetch Global pipeline.
    
    Architecture:
        1. Fire all 3 agents concurrently (EmailAgent, CalendarAgent, ReportAgent)
        2. Merge their outputs into a unified Master Context
        3. Send the Master Context to the selected LLM for analysis
        4. Return the structured AnalysisResponse
    """

    def __init__(self):
        self.email_agent = EmailAgent()
        self.calendar_agent = CalendarAgent()
        self.report_agent = ReportAgent()

    async def run_pipeline(self, credentials, provider: str = None, api_key: str = None):
        """Execute the full multi-agent pipeline.
        
        Args:
            credentials: Google OAuth2 credentials object
            provider: AI provider string (e.g. 'gemini/gemini-2.0-flash')
            api_key: BYOK API key from the user
            
        Returns:
            tuple: (analysis_result, raw_data_dict) where raw_data_dict contains
                   all the raw fetched data for database persistence.
        """
        # Stage 1: Concurrent data harvesting via all 3 agents
        email_result, calendar_result, report_result = await asyncio.gather(
            self.email_agent.fetch_and_classify(credentials),
            self.calendar_agent.fetch_and_analyze(credentials),
            self.report_agent.fetch_and_report(credentials),
        )

        # Stage 2: Build unified Master Context Prompt
        context_prompt = gemini_service.build_prompt(
            email_summaries=email_result["formatted"],
            calendar_events=calendar_result["formatted"],
            drive_files=report_result["formatted_drive"],
        )
        context_prompt += f"\n\nGoogle Sheets Data:\n{report_result['formatted_sheets']}"

        # Stage 3: Send to LLM for intelligent analysis
        analysis_result = await asyncio.to_thread(
            gemini_service.analyze_context,
            context_prompt,
            provider,
            api_key,
        )

        # Stage 4: Package raw data for persistence and frontend
        raw_data = {
            "emails": email_result["raw"],
            "calendar": calendar_result["raw"],
            "drive": report_result["raw_drive"],
            "sheets": report_result["raw_sheets"],
        }

        return analysis_result, raw_data
