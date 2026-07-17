# Developer Guide — Platform Kernel

## Adding a tenant resource

1. Add `workspace_id` FK (and prefer `created_by`, `deleted_at` when persisting).
2. In the router:

```python
@router.get("/things")
def list_things(ctx=Depends(require_permission(Permission.WORKSPACE_READ))):
    return ok([serialize(t) for t in ctx.query(Thing).all()])

@router.post("/things")
def create_thing(body: dict, db=Depends(get_db), ctx=Depends(require_permission(Permission.WORKSPACE_WRITE))):
    obj = Thing(name=body["name"])
    ctx.attach(obj)
    db.add(obj)
    db.commit()
    ctx.audit("thing.created", resource_type="thing", resource_id=str(obj.id))
    return ok(serialize(obj))
```

3. Never write `filter(Model.workspace_id == …)` in feature code.
4. Background work must use `with worker_tenant(workspace_id, …):`.
5. Cache keys via `tenant_cache_key(workspace_id, …)`.
6. UI: extend existing Workspace shell / Settings components only.

## Dependency injection

- `get_platform_ctx` — full kernel context  
- `get_workspace_ctx` — alias (backward compatible)  
- `require_permission(Permission.X)` — context + gate  
- `require_workspace_editor` / `require_workspace_admin` — role floor
