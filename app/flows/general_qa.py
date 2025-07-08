from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from .base import BaseFlow, FlowState, flow
from ..core.config import settings

@flow(name="general_qa", description="Answer general questions and provide helpful information")
class GeneralQAFlow(BaseFlow):
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        super().__init__()
    
    def _build_graph(self) -> StateGraph:
        """Build the general QA graph"""
        
        workflow = StateGraph(FlowState)
        
        # Add nodes
        workflow.add_node("analyze_question", self._analyze_question)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("finalize_response", self._finalize_response)
        
        # Set entry point
        workflow.set_entry_point("analyze_question")
        
        # Add edges
        workflow.add_edge("analyze_question", "generate_response")
        workflow.add_edge("generate_response", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow
    
    def _analyze_question(self, state: FlowState) -> FlowState:
        """Analyze the user's question to understand intent"""
        user_message = self.get_last_user_message(state)
        
        analysis_prompt = f"""
        Analyze the following user question and determine:
        1. The type of question (factual, opinion, how-to, etc.)
        2. The main topic or domain
        3. Any specific requirements or constraints
        
        User question: {user_message}
        
        Provide a brief analysis in JSON format:
        {{
            "question_type": "type",
            "topic": "main_topic",
            "requirements": ["req1", "req2"],
            "complexity": "low|medium|high"
        }}
        """
        
        response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
        analysis = response.content
        
        state["metadata"]["question_analysis"] = analysis
        state["current_step"] = "analyze_question"
        
        return state
    
    def _generate_response(self, state: FlowState) -> FlowState:
        """Generate a comprehensive response to the user's question"""
        user_message = self.get_last_user_message(state)
        analysis = state["metadata"].get("question_analysis", "")
        
        response_prompt = f"""
        Based on the following analysis and user question, provide a comprehensive and helpful response.
        
        Question Analysis: {analysis}
        User Question: {user_message}
        
        Provide a detailed, accurate, and helpful response. If the question requires specific information 
        that you don't have access to, acknowledge this and suggest alternative approaches.
        """
        
        response = self.llm.invoke([HumanMessage(content=response_prompt)])
        response_content = response.content
        
        state["metadata"]["generated_response"] = response_content
        state["current_step"] = "generate_response"
        
        return state
    
    def _finalize_response(self, state: FlowState) -> FlowState:
        """Finalize and format the response"""
        response_content = state["metadata"].get("generated_response", "")
        
        # Add the response to the conversation
        state = self.add_message(state, response_content, "assistant")
        state["current_step"] = "finalize_response"
        
        return state
    
    def get_description(self) -> str:
        return """
        General QA Flow:
        
        This flow handles general questions and provides comprehensive, helpful responses.
        
        Process:
        1. Analyze the question type and intent
        2. Generate a detailed response
        3. Format and present the response
        
        Features:
        - Question type analysis
        - Comprehensive response generation
        - Context-aware answers
        - Helpful explanations and suggestions
        """ 