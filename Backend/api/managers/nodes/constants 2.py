# TODO: This should all be moved to a .ini file

# Do `from constants import username, password, neo_http_ap, neo_bolt_ap, node_labels, relationship_types, list_queries`

username = 'neo4j'
password = 'n4j'    #Make sure the right password is being used
firebase_auth_key = 'AIzaSyBTJkLtEGDgdIXaDyCEnj7mao-y6E5x5pk'

#neo_http_ap = 'http://localhost:7474'
#neo_http_ap = 'http://192.168.56.101:7474'
neo_http_ap = 'http://192.168.2.221:7474'

#neo_bolt_ap = 'bolt://localhost:7687'
#neo_bolt_ap = 'bolt://192.168.56.101:7687'
neo_bolt_ap = 'bolt://192.168.2.221:7687'

node_labels = [
    'Consumer',
    'Organization',
    'Location',
    'Event',
    'Community',
    'Product'
    ]

relationship_types = [
    'purchased',
    'attended',
    'hosted',
    'was_at',
    'is_member_of',
    'happened_at',
    'has_presence_at',
    'is_offered_by',
    'available_at',
    'is_partnered_with',
    'is_friends_with',
    'is_purchased_with',
    'is_partnered_with',
    'is_near'
    ]

list_queries = {
    'Consumer': '''
    MATCH (consumer:Consumer) RETURN consumer LIMIT 1000
    ''',
    'Organization': '''
    MATCH (organization:Organization) RETURN organization LIMIT 1000
    ''',
    'Location': '''
    MATCH (location:Location) RETURN location LIMIT 1000
    ''',
    'Event': '''
    MATCH (event:Event) RETURN event LIMIT 1000
    ''',
    'Community': '''
    MATCH (community:Community) RETURN community LIMIT 1000
    ''',
    'Product': '''
    MATCH (product:Product) RETURN product LIMIT 1000
    '''
    }