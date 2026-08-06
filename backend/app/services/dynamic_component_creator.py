"""Dynamic component creation system for workflows."""

from typing import Dict, Optional, List
import os
import json
from datetime import datetime
from pathlib import Path


class ComponentDiscovery:
    """Discover workflow components on disk and in memory."""
    
    def __init__(self, component_dir: str = "components"):
        self.component_dir = Path(component_dir)
        self.component_registry = {}
        self._load_existing_components()
    
    def _load_existing_components(self):
        """Load existing components from disk."""
        if not self.component_dir.exists():
            self.component_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for component_file in self.component_dir.glob("*.json"):
            try:
                with open(component_file, 'r') as f:
                    component_data = json.load(f)
                    self.component_registry[component_data["name"]] = component_data
            except Exception as e:
                print(f"Error loading component {component_file}: {e}")
    
    def find_component(self, component_name: str) -> Optional[Dict]:
        """
        Find component by name.
        
        Args:
            component_name: Name of component to find
            
        Returns:
            Component data if found, None otherwise
        """
        # Check memory registry
        if component_name in self.component_registry:
            return self.component_registry[component_name]
        
        # Check disk
        component_file = self.component_dir / f"{component_name}.json"
        if component_file.exists():
            try:
                with open(component_file, 'r') as f:
                    component_data = json.load(f)
                    self.component_registry[component_name] = component_data
                    return component_data
            except Exception:
                return None
        
        return None
    
    def search_components(self, keywords: List[str]) -> List[Dict]:
        """
        Search for components by keywords.
        
        Args:
            keywords: Keywords to search for
            
        Returns:
            List of matching components
        """
        matching_components = []
        keywords_lower = [k.lower() for k in keywords]
        
        for component_name, component_data in self.component_registry.items():
            component_text = f"{component_name} {component_data.get('description', '')} {json.dumps(component_data.get('tags', []))}"
            component_text_lower = component_text.lower()
            
            if any(keyword in component_text_lower for keyword in keywords_lower):
                matching_components.append(component_data)
        
        return matching_components
    
    def list_all_components(self) -> List[Dict]:
        """List all available components."""
        return list(self.component_registry.values())


class DynamicComponentCreator:
    """Create workflow components dynamically using AI."""
    
    def __init__(self, component_discovery: ComponentDiscovery, user_api_key: Optional[str] = None):
        self.component_discovery = component_discovery
        self.user_api_key = user_api_key
    
    async def create_component_if_missing(self, component_name: str, purpose: str = "") -> Dict:
        """
        Create component if it doesn't exist.
        
        Args:
            component_name: Name of component to create/find
            purpose: Purpose/description of what the component should do
            
        Returns:
            Component data
        """
        # Check if component exists
        existing_component = self.component_discovery.find_component(component_name)
        if existing_component:
            return {
                "status": "found",
                "component": existing_component,
                "message": f"Component '{component_name}' found on disk"
            }
        
        # Create new component
        return await self._create_component(component_name, purpose)
    
    async def _create_component(self, component_name: str, purpose: str) -> Dict:
        """
        Create new component using AI.
        
        Args:
            component_name: Name of component to create
            purpose: Purpose of the component
            
        Returns:
            Created component data
        """
        if not self.user_api_key:
            return {
                "status": "error",
                "message": f"Cannot create component '{component_name}' without API key. Please add your API key in Settings → Model providers."
            }
        
        try:
            # Generate component specification using AI
            component_spec = await self._generate_component_spec(component_name, purpose)
            
            # Generate component code
            component_code = await self._generate_component_code(component_spec)
            
            # Create component data structure
            component_data = {
                "name": component_name,
                "description": component_spec.get("description", f"Auto-generated component for {purpose}"),
                "type": component_spec.get("type", "custom"),
                "inputs": component_spec.get("inputs", []),
                "outputs": component_spec.get("outputs", []),
                "configuration": component_spec.get("configuration", {}),
                "code": component_code,
                "tags": component_spec.get("tags", ["auto-generated"]),
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
            
            # Save to disk
            self._save_component_to_disk(component_name, component_data)
            
            # Register in discovery
            self.component_discovery.component_registry[component_name] = component_data
            
            return {
                "status": "created",
                "component": component_data,
                "message": f"Component '{component_name}' created successfully using AI"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create component '{component_name}': {str(e)}"
            }
    
    async def _generate_component_spec(self, component_name: str, purpose: str) -> Dict:
        """Generate component specification using AI."""
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Generate a specification for a workflow component named '{component_name}'.

Purpose: {purpose}

Please provide a JSON specification with:
- description: What this component does
- type: Component type (api_integration, data_processing, notification, logic, etc.)
- inputs: List of required input parameters with types
- outputs: List of outputs this component produces
- configuration: Configuration parameters needed
- tags: Relevant tags for categorization

Return only valid JSON, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        # Extract JSON from response
        try:
            # Try to parse JSON directly
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                return json.loads(response[json_start:json_end].strip())
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                return json.loads(response[json_start:json_end].strip())
            else:
                # Fallback to basic spec
                return {
                    "description": f"Component for {purpose}",
                    "type": "custom",
                    "inputs": [],
                    "outputs": [],
                    "configuration": {},
                    "tags": ["auto-generated"]
                }
    
    async def _generate_component_code(self, component_spec: Dict) -> str:
        """Generate component code using AI."""
        from app.services.global_chat_handler import GlobalChatHandler
        
        handler = GlobalChatHandler(self.user_api_key)
        
        prompt = f"""Generate Python code for a workflow component with this specification:

{json.dumps(component_spec, indent=2)}

The code should:
1. Be a class that inherits from BaseComponent
2. Implement an execute() method that takes inputs and returns outputs
3. Include proper error handling
4. Follow the specification exactly
5. Include docstrings and comments

Return only the Python code, no additional text."""
        
        response = await handler.handle(prompt, {}, {})
        
        # Extract code from response
        if "```python" in response:
            code_start = response.find("```python") + 9
            code_end = response.find("```", code_start)
            return response[code_start:code_end].strip()
        elif "```" in response:
            code_start = response.find("```") + 3
            code_end = response.find("```", code_start)
            return response[code_start:code_end].strip()
        else:
            return response
    
    def _save_component_to_disk(self, component_name: str, component_data: Dict):
        """Save component to disk."""
        component_file = self.component_discovery.component_dir / f"{component_name}.json"
        
        with open(component_file, 'w') as f:
            json.dump(component_data, f, indent=2)
    
    def set_api_key(self, api_key: str):
        """Set the user's API key."""
        self.user_api_key = api_key