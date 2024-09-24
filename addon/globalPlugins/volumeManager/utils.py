def doc(docString):
    def decorator(method):
        method.__doc__ = docString
        return method

    return decorator
