"""API-based requirement gathering for workflow nodes."""

from typing import Dict, Optional, List
import httpx
import json


class APIRequirementGatherer:
    """Gather workflow requirements using APIs and AI."""
    
    def __init__(self, user_api_key: Optional[str] = None):
        self.user_api_key = user_api_key
        self.web_search_api = "https://api.duckduckgo.com/"  # Free web search API
    
    async def gather_requirements(self, workflow_goal: str, context: Optional[Dict] = None) -> Dict:
        """
        Gather requirements for workflow using APIs.
        
        Args:
            workflow_goal: Description of what the workflow should do
            context: Additional context for requirements gathering
            
        Returns:
            Complete requirements specification
        """
        if not self.user_api_key:
            return self._generate_basic_requirements(workflow_goal)
        
        try:
            # Step 1: Analyze workflow goal
            analysis = await self._analyze_workflow_goal(workflow_goal)
            
            # Step 2: Search for best practices
            best_practices = await self._search_best_practices(analysis)
            
            # Step 3: Identify required components
            required_components = await self._identify_components(analysis, best_practices)
            
            # Step 4: Generate node configurations
            node_configs = await self._generate_node_configs(
                required_components,
                analysis,
                best_practices
            )
            
            return {
                "status": "success",
                "analysis": analysis,
                "best_practices": best_practices,
                "required_components": required_components,
                "node_configurations": node_configs
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to gather requirements: {str(e)}",
                "fallback": self._generate_basic_requirements(workflow_goal)
            }
    
    async def _analyze_workflow_goal(self, workflow_goal: str) -> Dict:
        """Analyze workflow goal using AI."""
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Analyze this workflow goal and provide a structured analysis:

Workflow Goal: {workflow_goal}

Provide JSON analysis with:
- domain: The domain/category (e.g., email_automation, data_processing, monitoring)
- complexity: low/medium/high
- key_features: List of key features needed
- potential_challenges: List of potential challenges
- recommended_approach: Best approach to implement
- data_requirements: What data inputs/outputs are needed

Return only valid JSON, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback basic analysis
            return {
                "domain": "general",
                "complexity": "medium",
                "key_features": ["automation"],
                "potential_challenges": ["configuration"],
                "recommended_approach": "step-by-step",
                "data_requirements": ["inputs", "outputs"]
            }
    
    async def _search_best_practices(self, analysis: Dict) -> List[Dict]:
        """Search for best practices using web search and AI."""
        domain = analysis.get("domain", "general")
        
        # Use AI to generate best practices
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Provide best practices for workflows in the {domain} domain.

Analysis: {json.dumps(analysis, indent=2)}

Provide JSON array of best practices with:
- practice: Description of the best practice
- importance: high/medium/low
- implementation: How to implement it

Return only valid JSON array, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return [
                {
                    "practice": "Start with simple implementation",
                    "importance": "high",
                    "implementation": "Build basic version first, then enhance"
                }
            ]
    
    async def _identify_components(self, analysis: Dict, best_practices: List[Dict]) -> List[Dict]:
        """Identify required components for the workflow."""
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Identify the components needed for this workflow:

Domain: {analysis.get('domain')}
Key Features: {analysis.get('key_features')}
Recommended Approach: {analysis.get('recommended_approach')}

Provide JSON array of components with:
- name: Component name
- type: Component type (api_integration, data_processing, notification, logic, etc.)
- purpose: What this component does
- required: Whether this component is essential

Return only valid JSON array, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback components based on domain
            domain = analysis.get("domain", "general")
            if "email" in domain:
                return [
                    {"name": "email_sender", "type": "notification", "purpose": "Send emails", "required": True},
                    {"name": "template_processor", "type": "data_processing", "purpose": "Process email templates", "required": True}
                ]
            else:
                return [
                    {"name": "data_processor", "type": "data_processing", "purpose": "Process data", "required": True},
                    {"name": "output_handler", "type": "logic", "purpose": "Handle outputs", "required": True}
                ]
    
    async def _generate_node_configs(self, components: List[Dict], analysis: Dict, best_practices: List[Dict]) -> List[Dict]:
        """Generate configurations for workflow nodes."""
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Generate node configurations for these workflow components:

Components: {json.dumps(components, indent=2)}
Analysis: {json.dumps(analysis, indent=2)}

For each component, provide JSON with:
- component_name: Name of the component
- configuration: Configuration parameters needed
- input_mapping: How to map inputs to this node
- output_mapping: How to map outputs from this node
- dependencies: Which other nodes this depends on

Return only valid JSON array, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback basic configs
            return [
                {
                    "component_name": comp["name"],
                    "configuration": {},
                    "input_mapping": {},
                    "output_mapping": {},
                    "dependencies": []
                }
                for comp in components
            ]
    
    async def gather_node_data_via_api(self, node_config: Dict, user_api_key: str) -> Dict:
        """
        Gather specific data for a node via APIs.
        
        Args:
            node_config: Node configuration
            user_api_key: User's API key for AI calls
            
        Returns:
            Node-specific data
        """
        self.user_api_key = user_api_key
        
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(user_api_key)
        
        prompt = f"""Gather configuration data for this workflow node:

Node Configuration: {json.dumps(node_config, indent=2)}

Research and provide:
- API endpoints if needed
- Authentication requirements
- Data format specifications
- Example values for configuration
- Best practices for this specific node type

Return valid JSON with all gathered data."""
        
        response = await handler.handle(prompt, {}, {})
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "status": "partial",
                "message": "Could not gather full API data",
                "suggestion": "Manual configuration may be needed"
            }
    
    def _generate_basic_requirements(self, workflow_goal: str) -> Dict:
        """Generate basic requirements without API."""
        return {
            "status": "basic",
            "message": "Basic requirements generated (API key needed for full requirements)",
            "analysis": {
                "domain": "general",
                "complexity": "medium",
                "key_features": ["automation"],
                "data_requirements": ["inputs", "outputs"]
            },
            "required_components": [
                {"name": "input_handler", "type": "logic", "purpose": "Handle inputs", "required": True},
                {"name": "processor", "type": "data_processing", "purpose": "Process data", "required": True},
                {"name": "output_handler", "type": "logic", "purpose": "Handle outputs", "required": True}
            ],
            "node_configurations": [
                {
                    "component_name": "input_handler",
                    "configuration": {},
                    "input_mapping": {},
                    "output_mapping": {},
                    "dependencies": []
                },
                {
                    "component_name": "processor",
                    "configuration": {},
                    "input_mapping": {},
                    "output_mapping": {},
                    "dependencies": ["input_handler"]
                },
                {
                    "component_name": "output_handler",
                    "configuration": {},
                    "input_mapping": {},
                    "output_mapping": {},
                    "dependencies": ["processor"]
                }
            ]
        }
    
    def set_api_key(self, api_key: str):
        """Set the user's API key."""
        self.user_api_key = api_key