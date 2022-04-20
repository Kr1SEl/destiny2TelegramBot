classes = {
    "0": "\U0001F981 <b>Titan</b>",
    "1": "\U0001F40D <b>Hunter</b>",
    "2": "\U0001F985 <b>Warlock</b>",
    "3": "\U0001F914 <b>Unknown</b>"
}

# Use profile records to obtain data

raids = {
    '\U0001F98B Vow of the Disciple': '2168422218',
    '\U0001F48E Vault of Glass': '3114569402',
    '\U0001F5FF Deep Stone Crypt': '3185876102',
    '\U0001F313 Garden of Salvation':  '3804486505',
    '\U0001F30C Last Wish': '3448775736',
    '\U0001F451 Crown of Sorrow': '3292013047',
    '\U0001F916 Scourge of the Past': '1455741693',
    '\U0001F47E Spire of Stars': '3996781284',
    '\U0001F990 Eater of Worlds': '1627755918',
    '\U0001F3C6 Leviathan': '2266286943'
}

locations = {
    'European Dead Zone': '3747705955',
    'Tower': '3747705955',
    'Nessus': 'unknown'
}

statHashes = {
    'Crucible Matches': '4181381577',
    'Crucible Matches Won': '3561485187',
    'Oponents Defeated': '1897223897',
}


def integerFromString(someString):
    try:
        newValue = int(someString)
        return newValue
    except ValueError as ve:
        return 0
