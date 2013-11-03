from functools import wraps


def add_response_headers(headers={}):
    """
    Add a dictionary of response headers to a request
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = func(*args, **kwargs)
            if headers:
                return resp, 200, headers
            else:
                return resp
        return wrapper
    return decorator

def nocache(func):
    """
    This decorator passes adds a noache header
    """
    @wraps(func)
    @add_response_headers({'Cache-Control': 'no-cache=true, private=true, no-store, must-revalidate'})
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper