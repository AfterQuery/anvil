from typing import Optional


def register_routes(app):
    """Register HTTP routes used by the example application.

    The platform tests expect the `/api/profile` endpoint to exist and to
    call into `userService.get_profile`. Keep the route path and function
    name (`profile`) intact when modifying this file.
    """

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/api/profile")
    def profile():
        # Lightweight header-based auth helper used for the example.
        from .utils import require_auth
        from .service import userService
        import flask

        # Return 401 if the incoming request does not provide the expected token.
        if not require_auth(flask.request.headers):
            return ("", 401)

        # For the small demo we assume user id 1 is the authenticated user.
        svc = userService()
        profile_data = svc.get_profile(1)
        if profile_data is None:
            return ("", 404)
        return profile_data

