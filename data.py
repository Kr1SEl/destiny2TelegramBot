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
    '\U0000269C Crown of Sorrow': '3292013047',
    '\U0000269C Scourge of the Past': '1455741693',
    '\U0000269C Spire of Stars': '3996781284',
    '\U0000269C Eater of Worlds': '1627755918',
    '\U0000269C Leviathan': '2266286943'
}


def integerFromString(someString):
    try:
        newValue = int(someString)
        return newValue
    except ValueError as ve:
        return 0
