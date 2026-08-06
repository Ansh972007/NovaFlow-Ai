"""Intent classification system for universal AI chat."""

from typing import Dict, List, Optional
from enum import Enum
import re


class IntentType(Enum):
    """Types of user intents."""
    GENERAL_QUESTION = "general_question"
    WORKFLOW_BUILDING = "workflow_building"
    WORKFLOW_EXECUTION = "workflow_execution"
    COMPONENT_CREATION = "component_creation"
    API_INTEGRATION = "api_integration"
    WORKFLOW_MANAGEMENT = "workflow_management"
    HYBRID = "hybrid"


class IntentClassifier:
    """Classify user intent to route to appropriate handler."""
    
    def __init__(self):
        self.patterns = {
            IntentType.GENERAL_QUESTION: [
                r"what is|how do|how to|why|explain|tell me about|describe",
                r"best way|best practice|recommend|suggest",
                r"meaning|definition|difference between",
                r"help me understand|can you explain"
            ],
            IntentType.WORKFLOW_BUILDING: [
                r"create workflow|build workflow|make workflow|design workflow",
                r"automate|automation|workflow for|to automate",
                r"new workflow|add workflow|setup workflow"
            ],
            IntentType.WORKFLOW_EXECUTION: [
                r"run workflow|execute workflow|start workflow",
                r"test workflow|try workflow|workflow run"
            ],
            IntentType.COMPONENT_CREATION: [
                r"create component|make component|new component",
                r"add component|build component|component for"
            ],
            IntentType.API_INTEGRATION: [
                r"integrate|connect|api|webhook|external",
                r"fetch data|get data|pull data|sync"
            ],
            IntentType.WORKFLOW_MANAGEMENT: [
                r"list workflow|show workflow|my workflow",
                r"update workflow|edit workflow|modify workflow",
                r"delete workflow|remove workflow"
            ]
        }
    
    def classify(self, user_input: str, context: Optional[Dict] = None) -> IntentType:
        """
        Classify user intent from input.
        
        Args:
            user_input: User's message
            context: Conversation context for better classification
            
        Returns:
            IntentType: The classified intent
        """
        lower_input = user_input.lower()
        
        # Check each intent type
        intent_scores = {}
        for intent_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, lower_input):
                    score += 1
            intent_scores[intent_type] = score
        
        # Find highest scoring intent
        max_score = max(intent_scores.values())
        if max_score == 0:
            # Default to general question if no patterns match
            return IntentType.GENERAL_QUESTION
        
        # Check for hybrid intent (multiple high scores)
        high_scoring_intents = [
            intent for intent, score in intent_scores.items() 
            if score >= max_score - 1
        ]
        
        if len(high_scoring_intents) > 1:
            return IntentType.HYBRID
        
        # Return single highest scoring intent
        return max(intent_scores, key=intent_scores.get)
    
    def extract_entities(self, user_input: str, intent: IntentType) -> Dict[str, str]:
        """
        Extract entities from user input based on intent.
        
        Args:
            user_input: User's message
            intent: Classified intent
            
        Returns:
            Dict of extracted entities
        """
        entities = {}
        lower_input = user_input.lower()
        
        if intent == IntentType.WORKFLOW_BUILDING:
            # Extract workflow purpose
            if "for" in lower_input:
                entities["purpose"] = lower_input.split("for")[-1].strip()
            if "to" in lower_input:
                entities["purpose"] = lower_input.split("to")[-1].strip()
        
        elif intent == IntentType.WORKFLOW_EXECUTION:
            # Extract workflow identifier
            if "workflow" in lower_input:
                parts = lower_input.split("workflow")
                if len(parts) > 1:
                    entities["workflow_id"] = parts[-1].strip()
        
        elif intent == IntentType.COMPONENT_CREATION:
            # Extract component type
            if "component" in lower_input:
                parts = lower_input.split("component")
                if len(parts) > 1:
                    entities["component_type"] = parts[-1].strip()
        
        elif intent == IntentType.API_INTEGRATION:
            # Extract API/service name
            api_keywords = ["twitter", "gmail", "slack", "github", "stripe", "api"]
            for keyword in api_keywords:
                if keyword in lower_input:
                    entities["service"] = keyword
        
        return entities
    
    def get_confidence(self, user_input: str, intent: IntentType) -> float:
        """
        Get confidence score for intent classification.
        
        Args:
            user_input: User's message
            intent: Classified intent
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        lower_input = user_input.lower()
        patterns = self.patterns.get(intent, [])
        
        matches = sum(1 for pattern in patterns if re.search(pattern, lower_input))
        total_patterns = len(patterns)
        
        if total_patterns == 0:
            return 0.5
        
        return min(matches / total_patterns, 1.0)


class ResponseRouter:
    """Route user requests to appropriate handlers based on intent."""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.handlers = {}
    
    def register_handler(self, intent: IntentType, handler):
        """Register a handler for a specific intent."""
        self.handlers[intent] = handler
    
    async def route(self, user_input: str, context: Optional[Dict] = None) -> Dict:
        """
        Route user request to appropriate handler.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Handler response
        """
        # Classify intent
        intent = self.intent_classifier.classify(user_input, context)
        entities = self.intent_classifier.extract_entities(user_input, intent)
        confidence = self.intent_classifier.get_confidence(user_input, intent)
        
        # Get handler
        handler = self.handlers.get(intent)
        if not handler:
            # Default to general question handler
            handler = self.handlers.get(IntentType.GENERAL_QUESTION)
        
        if not handler:
            return {
                "error": "No handler available for this request",
                "intent": intent.value,
                "confidence": confidence
            }
        
        # Call handler
        try:
            response = await handler.handle(user_input, entities, context)
            return {
                "response": response,
                "intent": intent.value,
                "confidence": confidence,
                "entities": entities
            }
        except Exception as e:
            return {
                "error": str(e),
                "intent": intent.value,
                "confidence": confidence
            }