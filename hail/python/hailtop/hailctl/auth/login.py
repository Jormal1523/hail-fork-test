import json
import os

from hailtop.auth import AzureFlow, GoogleFlow, IdentityProvider, hail_credentials
from hailtop.config import DeployConfig, get_deploy_config, get_hail_config_path, get_user_identity_config_path
from hailtop.httpx import ClientSession, client_session


async def auth_flow(deploy_config: DeployConfig, session: ClientSession):
    resp = await session.get_read_json(deploy_config.url('auth', '/api/v1alpha/oauth2-client'))
    idp = IdentityProvider(resp['idp'])
    client_secret_config = resp['oauth2_client']
    if idp == IdentityProvider.GOOGLE:
        credentials = GoogleFlow.perform_installed_app_login_flow(client_secret_config)
    else:
        assert idp == IdentityProvider.MICROSOFT
        credentials = AzureFlow.perform_installed_app_login_flow(client_secret_config)

    os.makedirs(get_hail_config_path(), exist_ok=True)
    with open(get_user_identity_config_path(), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'idp': idp.value, 'credentials': credentials}))

    # Confirm that the logged in user is registered with the hail service
    async with hail_credentials(deploy_config=deploy_config) as c:
        headers_with_auth = await c.auth_headers()
    async with client_session(headers=headers_with_auth) as auth_session:
        userinfo = await auth_session.get_read_json(deploy_config.url('auth', '/api/v1alpha/userinfo'))

    username = userinfo['username']
    print(f'Logged into {deploy_config.base_url("auth")} as {username}.')


async def async_login():
    deploy_config = get_deploy_config()
    async with hail_credentials(deploy_config=deploy_config, authorize_target=False) as credentials:
        headers = await credentials.auth_headers()
    async with client_session(headers=headers) as session:
        await auth_flow(deploy_config, session)
