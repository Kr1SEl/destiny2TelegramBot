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
    '⚜️ Leviathan': '2266286943'
}

# locations = {
#     'European Dead Zone': '697502628',
#     'Tower': '1737926756',
#     'Nessus': '3607432451'
# }

# indexes are important!!!
locations = ['Tower \U0001F5FC', 'EDZ \U000026F0', 'Nessus \U0001F4A0']

#    "locations": [
#        {
#            "backgroundImagePath": "/img/destiny_content/pgcr/conceptual_xur.jpg",
#            "destinationHash": 1737926756 -- TOWER
#        },
#        {
#            "backgroundImagePath": "/img/destiny_content/pgcr/conceptual_xur.jpg",
#            "destinationHash": 697502628  -- EMZ
#        },
#        {
#            "backgroundImagePath": "/img/destiny_content/pgcr/conceptual_xur.jpg",
#            "destinationHash": 3607432451 -- NESSUS
#        }
#    ]


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
