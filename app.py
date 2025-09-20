import os
import time
from typing import TypedDict, List, Dict, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from langgraph.graph import Graph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage


class GhanaTaxAgent:
    def __init__(self, llm_api_key: str = None):
        """Initialize the Ghana Tax Agent with optional LLM API key"""
        self.llm_api_key = llm_api_key
        self.llm = None
        self.driver = None
        
        if llm_api_key:
            try:
                self.llm = ChatOpenAI(
                    api_key=llm_api_key,
                    model="gpt-3.5-turbo",
                    temperature=0.7
                )
            except Exception as e:
                print(f"LLM initialization failed: {e}. Using fallback budget generation.")
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> Graph:
        """Build the LangGraph workflow"""
        workflow = Graph()
        
        # Add nodes
        workflow.add_node("scrape_tax", self.scrape_tax_calculator)
        workflow.add_node("generate_budget", self.generate_budget)
        workflow.add_node("create_pdf", self.create_pdf)
        
        # Define edges
        workflow.add_edge("scrape_tax", "generate_budget")
        workflow.add_edge("generate_budget", "create_pdf")
        workflow.add_edge("create_pdf", END)
        
        # Set entry point
        workflow.set_entry_point("scrape_tax")
        
        return workflow.compile()