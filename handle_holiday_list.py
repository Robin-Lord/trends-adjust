import holidays


def return_available_countries():
    # Get the list of available countries
    return ["None"]+[country for country in holidays.list_supported_countries()]
