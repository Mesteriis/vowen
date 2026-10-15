async def test_public_instance_name_has_no_secrets(api):
    client, app = api
    app.state.settings.app_display_name = "Synthetic workspace"
    response = await client.get("/api/v1/instance")
    assert response.status_code == 200
    assert response.json() == {"display_name": "Synthetic workspace"}
