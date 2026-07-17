def test_run_workflow_endpoint_executes_full_workflow(client):
    response = client.post("/workflow/run")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_stages"] == [
        "Planner Agent",
        "Research Agent",
        "Knowledge Agent",
        "Opportunity Analysis Agent",
        "Content Generation Agent",
        "Reporting Agent",
    ]
    assert body["errors"] == []
