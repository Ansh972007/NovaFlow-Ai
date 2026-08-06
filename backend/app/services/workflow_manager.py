"""High-level workflow management service for chat interactions."""

from typing import Any, List, Dict
from sqlalchemy.orm import Session
from app.database import Workflow, WorkflowRun, WorkflowVersion
from app.services.workflow import list_workflow_versions, restore_workflow_version
from datetime import datetime


class WorkflowManager:
    """High-level workflow management for chat interactions."""
    
    def __init__(self, db: Session, user_id: int, workspace_id: int):
        self.db = db
        self.user_id = user_id
        self.workspace_id = workspace_id
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows available to the user."""
        workflows = self.db.query(Workflow).filter(
            Workflow.workspace_id == self.workspace_id,
            Workflow.delete == 0
        ).order_by(Workflow.update_time.desc()).all()
        
        return [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description or "",
                "status": "published" if wf.status == 1 else "draft",
                "updated_at": wf.update_time.isoformat() if wf.update_time else None,
                "type": "workflow"
            }
            for wf in workflows
        ]
    
    def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific workflow."""
        workflow = self.db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.workspace_id == self.workspace_id,
            Workflow.delete == 0
        ).first()
        
        if not workflow:
            return {"error": "Workflow not found"}
        
        # Get recent runs
        recent_runs = self.db.query(WorkflowRun).filter(
            WorkflowRun.workflow_id == workflow_id
        ).order_by(WorkflowRun.create_time.desc()).limit(5).all()
        
        # Get versions
        versions = list_workflow_versions(self.db, workflow_id)
        
        return {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description or "",
            "status": "published" if workflow.status == 1 else "draft",
            "graph": workflow.graph or {},
            "updated_at": workflow.update_time.isoformat() if workflow.update_time else None,
            "recent_runs": [
                {
                    "id": run.id,
                    "status": "completed" if run.status == 1 else "error",
                    "created_at": run.create_time.isoformat() if run.create_time else None
                }
                for run in recent_runs
            ],
            "versions": versions,
            "type": "workflow"
        }
    
    def format_workflow_list(self, workflows: List[Dict[str, Any]]) -> str:
        """Format workflow list for chat display."""
        if not workflows:
            return "You don't have any workflows yet. Would you like me to help you create one?"
        
        response = f"You have {len(workflows)} workflow(s):\n\n"
        for i, wf in enumerate(workflows, 1):
            status_emoji = "✅" if wf["status"] == "published" else "📝"
            response += f"{i}. {status_emoji} **{wf['name']}**"
            if wf.get("description"):
                response += f" - {wf['description']}"
            response += f" (ID: {wf['id']})\n"
        
        response += "\nYou can ask me to:\n"
        response += "• **Run** a specific workflow\n"
        response += "• **Test** a workflow\n"
        response += "• **Update** a workflow\n"
        response += "• **Delete** a workflow\n"
        response += "• **View details** about a workflow\n"
        response += "\nWhich workflow would you like to work with?"
        
        return response
    
    def format_workflow_details(self, details: Dict[str, Any]) -> str:
        """Format workflow details for chat display."""
        if "error" in details:
            return f"Error: {details['error']}"
        
        response = f"**{details['name']}** ({details['status']})\n\n"
        
        if details.get("description"):
            response += f"Description: {details['description']}\n\n"
        
        response += f"Last updated: {details['updated_at']}\n\n"
        
        if details.get("recent_runs"):
            response += "Recent runs:\n"
            for run in details["recent_runs"]:
                status_emoji = "✅" if run["status"] == "completed" else "❌"
                response += f"  {status_emoji} {run['created_at']} - {run['status']}\n"
            response += "\n"
        
        if details.get("versions"):
            response += f"Available versions: {len(details['versions'])}\n"
        
        response += "\nAvailable actions:\n"
        response += "• **Run** this workflow\n"
        response += "• **Test** this workflow\n"
        response += "• **Update** this workflow\n"
        response += "• **Delete** this workflow\n"
        response += "• **View versions**\n"
        
        return response
    
    def suggest_workflow_action(self, user_input: str) -> str:
        """Suggest appropriate workflow actions based on user input."""
        lower_input = user_input.lower()
        
        suggestions = []
        
        # Workflow selection
        if any(word in lower_input for word in ["which", "what", "list", "show", "workflows"]):
            workflows = self.list_workflows()
            return self.format_workflow_list(workflows)
        
        # Run workflow
        if any(word in lower_input for word in ["run", "execute", "start"]):
            suggestions.append("Which workflow would you like to run?")
            workflows = self.list_workflows()
            if workflows:
                suggestions.append("\nHere are your available workflows:")
                for wf in workflows[:5]:
                    suggestions.append(f"• {wf['name']} (ID: {wf['id']})")
            return "\n".join(suggestions)
        
        # Test workflow
        if any(word in lower_input for word in ["test", "try", "sandbox"]):
            suggestions.append("Which workflow would you like to test?")
            workflows = self.list_workflows()
            if workflows:
                suggestions.append("\nHere are your available workflows:")
                for wf in workflows[:5]:
                    suggestions.append(f"• {wf['name']} (ID: {wf['id']})")
            return "\n".join(suggestions)
        
        # Update workflow
        if any(word in lower_input for word in ["update", "edit", "modify", "change"]):
            suggestions.append("Which workflow would you like to update?")
            workflows = self.list_workflows()
            if workflows:
                suggestions.append("\nHere are your available workflows:")
                for wf in workflows[:5]:
                    suggestions.append(f"• {wf['name']} (ID: {wf['id']})")
            return "\n".join(suggestions)
        
        # Delete workflow
        if any(word in lower_input for word in ["delete", "remove", "get rid of"]):
            suggestions.append("Which workflow would you like to delete?")
            workflows = self.list_workflows()
            if workflows:
                suggestions.append("\nHere are your available workflows:")
                for wf in workflows[:5]:
                    suggestions.append(f"• {wf['name']} (ID: {wf['id']})")
            suggestions.append("\n⚠️ **Warning**: This action cannot be undone!")
            return "\n".join(suggestions)
        
        # Default suggestion
        workflows = self.list_workflows()
        if workflows:
            return f"I can help you manage your {len(workflows)} workflow(s). Here's what I can do:\n\n" + \
                   "• **List workflows** - Show all your workflows\n" + \
                   "• **Run workflow** - Execute a specific workflow\n" + \
                   "• **Test workflow** - Test a workflow in sandbox mode\n" + \
                   "• **Update workflow** - Modify an existing workflow\n" + \
                   "• **Delete workflow** - Remove a workflow\n" + \
                   "• **View details** - Get detailed information about a workflow\n\n" + \
                   "What would you like to do?"
        else:
            return "You don't have any workflows yet. I can help you create one! Just describe what you'd like to automate, and I'll guide you through the process."