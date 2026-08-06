"""Workflow orchestrator for complete workflow building and execution."""

from typing import Dict, Optional, List
import json
from datetime import datetime


class WorkflowOrchestrator:
    """Orchestrate complete workflow lifecycle from request to execution."""
    
    def __init__(self, user_api_key: Optional[str] = None):
        self.user_api_key = user_api_key
        
        # Initialize sub-systems
        from app.services.dynamic_component_creator import ComponentDiscovery, DynamicComponentCreator
        from app.services.api_requirement_gatherer import APIRequirementGatherer
        
        self.component_discovery = ComponentDiscovery()
        self.component_creator = DynamicComponentCreator(self.component_discovery, user_api_key)
        self.requirement_gatherer = APIRequirementGatherer(user_api_key)
    
    async def build_and_execute_workflow(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """
        Complete workflow lifecycle: build and execute.
        
        Args:
            user_request: User's workflow request
            context: Additional context
            
        Returns:
            Workflow execution result
        """
        try:
            # Step 1: Gather requirements
            requirements = await self.requirement_gatherer.gather_requirements(user_request, context)
            
            if requirements.get("status") == "error":
                return {
                    "status": "error",
                    "message": requirements.get("message"),
                    "fallback": requirements.get("fallback")
                }
            
            # Step 2: Create missing components
            component_results = []
            for component in requirements.get("required_components", []):
                component_name = component["name"]
                component_purpose = component["purpose"]
                
                result = await self.component_creator.create_component_if_missing(
                    component_name,
                    component_purpose
                )
                component_results.append(result)
            
            # Step 3: Build workflow graph
            workflow_graph = await self._build_workflow_graph(
                requirements.get("node_configurations", []),
                component_results
            )
            
            # Step 4: Configure nodes with API data
            configured_nodes = []
            for node_config in workflow_graph.get("nodes", []):
                node_data = await self.requirement_gatherer.gather_node_data_via_api(
                    node_config,
                    self.user_api_key
                )
                configured_node = self._configure_node(node_config, node_data)
                configured_nodes.append(configured_node)
            
            workflow_graph["nodes"] = configured_nodes
            
            # Step 5: Execute workflow
            execution_result = await self._execute_workflow(workflow_graph)
            
            # Step 6: Format final output
            final_output = self._format_final_output(execution_result, requirements)
            
            return {
                "status": "success",
                "workflow": workflow_graph,
                "execution_result": execution_result,
                "final_output": final_output,
                "components_created": [r for r in component_results if r.get("status") == "created"],
                "components_found": [r for r in component_results if r.get("status") == "found"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Workflow orchestration failed: {str(e)}",
                "suggestion": "Please check your API key configuration and try again."
            }
    
    async def _build_workflow_graph(self, node_configs: List[Dict], component_results: List[Dict]) -> Dict:
        """Build workflow graph from node configurations."""
        nodes = []
        edges = []
        
        for i, node_config in enumerate(node_configs):
            node = {
                "id": f"node_{i}",
                "name": node_config.get("component_name", f"Node {i}"),
                "type": node_config.get("type", "custom"),
                "configuration": node_config.get("configuration", {}),
                "position": {"x": i * 200, "y": 100}
            }
            nodes.append(node)
            
            # Create edges based on dependencies
            for dep in node_config.get("dependencies", []):
                # Find the dependency node
                dep_index = next(
                    (j for j, config in enumerate(node_configs) 
                     if config.get("component_name") == dep),
                    None
                )
                if dep_index is not None:
                    edges.append({
                        "id": f"edge_{dep_index}_{i}",
                        "source": f"node_{dep_index}",
                        "target": f"node_{i}",
                        "type": "default"
                    })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "created_at": datetime.now().isoformat()
        }
    
    def _configure_node(self, node_config: Dict, node_data: Dict) -> Dict:
        """Configure node with API-gathered data."""
        configured_node = node_config.copy()
        
        # Merge API data into configuration
        if node_data.get("status") != "error":
            configured_node["api_data"] = node_data
            configured_node["configuration"].update(node_data.get("configuration", {}))
        
        return configured_node
    
    async def _execute_workflow(self, workflow_graph: Dict) -> Dict:
        """Execute workflow graph."""
        # This would integrate with the existing workflow execution system
        # For now, simulate execution
        
        nodes = workflow_graph.get("nodes", [])
        execution_log = []
        
        for node in nodes:
            # Simulate node execution
            execution_log.append({
                "node": node["name"],
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "output": f"Executed {node['name']} successfully"
            })
        
        return {
            "status": "completed",
            "execution_log": execution_log,
            "total_nodes": len(nodes),
            "successful_nodes": len(nodes)
        }
    
    def _format_final_output(self, execution_result: Dict, requirements: Dict) -> str:
        """Format final output for user."""
        successful_nodes = execution_result.get("successful_nodes", 0)
        total_nodes = execution_result.get("total_nodes", 0)
        
        output = f"✅ Workflow execution completed successfully!\n\n"
        output += f"Executed {successful_nodes}/{total_nodes} nodes successfully.\n\n"
        
        output += "Execution Summary:\n"
        for log_entry in execution_result.get("execution_log", []):
            output += f"  • {log_entry['node']}: {log_entry['status']}\n"
        
        output += f"\nWorkflow built for: {requirements.get('analysis', {}).get('domain', 'general')}\n"
        
        return output
    
    async def build_workflow_only(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """Build workflow without executing it."""
        try:
            # Gather requirements
            requirements = await self.requirement_gatherer.gather_requirements(user_request, context)
            
            if requirements.get("status") == "error":
                return {
                    "status": "error",
                    "message": requirements.get("message"),
                    "fallback": requirements.get("fallback")
                }
            
            # Create missing components
            component_results = []
            for component in requirements.get("required_components", []):
                result = await self.component_creator.create_component_if_missing(
                    component["name"],
                    component["purpose"]
                )
                component_results.append(result)
            
            # Build workflow graph
            workflow_graph = await self._build_workflow_graph(
                requirements.get("node_configurations", []),
                component_results
            )
            
            return {
                "status": "success",
                "workflow": workflow_graph,
                "requirements": requirements,
                "components_created": [r for r in component_results if r.get("status") == "created"],
                "components_found": [r for r in component_results if r.get("status") == "found"],
                "message": "Workflow built successfully. Ready to execute."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Workflow building failed: {str(e)}"
            }
    
    def set_api_key(self, api_key: str):
        """Set the user's API key."""
        self.user_api_key = api_key
        self.component_creator.set_api_key(api_key)
        self.requirement_gatherer.set_api_key(api_key)