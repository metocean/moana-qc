def catch(func, handle=lambda e : e, *args, **kwargs):
    ''' Values that return an error are overwritten as np.nan...we just ignore them for now '''
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return np.nan