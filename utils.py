import requests
from io import StringIO




def get_data_from_API_call(url):
    """
    Send a GET request to the specified URL and return the response
    content as a file-like StringIO object.

    Parameters
    ----------
    url : str
        The complete endpoint URL from which data will be fetched.

    Returns
    -------
    io.StringIO
        A file-like object containing the UTF-8 decoded response text.

    Raises
    ------
    Exception
        If the HTTP status code is anything other than 200, an
        exception is raised with a message that includes the received
        status code.
    """
    # Send HTTP GET request
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        data = StringIO(response.content.decode("utf-8"))
        return data
    else:
        print("Failed to retrieve data. Status code:", response.status_code)    
        raise Exception(f"Failed to retrieve data. Status code: {response.status_code}")