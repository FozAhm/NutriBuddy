#Dump for neo4j queries related to node managers


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~GETTING NODE ID FROM OTHER INFORMATION~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#Searched database for community uuid and returns the neo4j node id for manipulations
get_community_id_by_uuid = '''
MATCH (com:Community) WHERE com.uuid = $uuid
RETURN id(com)
'''

#Searched database for consumer uuid and returns the neo4j node id for manipulations
get_consumer_id_by_uuid = '''
MATCH (con:Consumer) WHERE con.uuid = $uuid
RETURN id(con)
'''

#Searched database for consumer firbase id and returns the neo4j node id for manipulations
get_consumer_id_by_fbid = '''
MATCH (con:Consumer) WHERE con.firebase_id = $fbid
RETURN id(con)
'''

#Searched database for event uuid and returns the neo4j node id for manipulations
get_event_id_by_uuid = '''
MATCH (event:Event) WHERE event.uuid = $uuid
RETURN id(event)
'''

#Searched database for location uuid and returns the neo4j node id for manipulations
get_location_id_by_uuid = '''
MATCH (loc:Location) WHERE loc.uuid = $uuid
RETURN id(loc)
'''
#Searched database for location uuid and returns the neo4j node id for manipulations
get_organization_id_by_uuid = '''
MATCH (org:Organization) WHERE org.uuid = $uuid
RETURN id(org)
'''

#Searched database for product uuid and returns the neo4j node id for manipulations
get_product_id_by_uuid = '''
MATCH (pro:Product) WHERE pro.uuid = $uuid
RETURN id(pro)
'''

#Searched database for product UPC and returns the neo4j node id for manipulations
get_product_id_by_UPC = '''
MATCH (pro:Product) WHERE pro.UPC = $UPC
RETURN id(pro)
'''

get_product_id_by_beacon='''
MATCH (pro:Product)-[aa:available_at]->(loc:Location)
WHERE aa.beacon_id = $target_beacon_id
RETURN id(pro)
'''

#Searched database for purchase uuid and returns the neo4j node id for manipulations
get_purchase_id_by_uuid = '''
MATCH (pur:Purchase) WHERE pur.uuid = $uuid
RETURN id(pur)
'''

#Searched database for raincheck uuid and returns the neo4j node id for manipulations
get_raincheck_id_by_uuid = '''
MATCH (rai:Raincheck) WHERE rai.uuid = $uuid
RETURN id(rai)
'''

get_receipt_id_by_uuid='''
MATCH (rec:Receipt) WHERE rec.uuid = $uuid
RETURN id(rec)
'''

get_employee_id_by_uuid ='''
MATCH (empl:Employee) WHERE empl.uuid = $uuid
RETURN id(empl)
'''

#Searched database for consumer firbase id and returns the neo4j node id for manipulations
get_employee_id_by_fbid = '''
MATCH (empl:Employee) WHERE empl.firebase_id = $fbid
RETURN id(empl)
'''
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Relationship Finding~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#Returning a consumer's wishlist
get_full_wishlist='''
MATCH (c:Consumer)-[:wishlisted]->(p:Product) WHERE c.uuid = $uuid
RETURN p LIMIT 500
'''

get_full_basket='''
MATCH (c:Consumer)-[b:basketed]->(p:Product) WHERE c.uuid = $uuid
RETURN p,b LIMIT 500
'''

#Returning a consumer's communities
get_full_communities='''
MATCH (c:Consumer)-[:is_member_of]->(t:Community) WHERE c.uuid = $uuid
RETURN t LIMIT 500
'''

get_full_purchases='''
MATCH (p:Purchase)-[:composes]->(r:Receipt) WHERE r.uuid = $uuid
RETURN p LIMIT 500
'''

get_branches_id='''
MATCH (o:Organization)-[b:branched]->(l:Location)
WHERE o.uuid = $uuid
RETURN id(l)
'''

get_branches_aa_id='''
MATCH (o:Organization)-[b:branched]->(l:Location)<-[aa:available_at]-(p:Product)
WHERE o.uuid = $uuido AND p.uuid = $uuidp
RETURN id(aa)
'''

get_product_locations='''
MATCH (p:Product)-[aa:available_at]->(l:Location)
WHERE p.uuid = $uuid
RETURN l 
'''

get_location_products='''
MATCH (p:Product)-[aa:available_at]->(l:Location)
WHERE l.uuid = $uuid
RETURN p
'''

########### Labels can't be parameterized in cypher, so for optimization a different query is needed for each
get_all_orgs='''
MATCH (n:Organization)
RETURN n
'''

get_all_consumers='''
MATCH (n:Consumer)
RETURN n
'''

get_all_loyalty_tracker='''
MATCH(c:Consumer)-[rel:loyalty_tracker]->(o:Organization)
WHERE c.uuid = $uuid AND NOT rel.points = '0'
RETURN rel, o
'''

get_all_friends = '''
MATCH (a:Consumer)-[rel:is_friends_with]-(b:Consumer)
WHERE a.uuid = $uuid
return b
'''

get_is_member_of='''
MATCH (a:Consumer)-[rel:is_member_of]->(b:Community)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_is_friends_with='''
MATCH (a:Consumer)-[rel:following]-(b:Consumer)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''#Relation is non-directional on purpose

get_following='''
MATCH (a:Consumer)-[rel:following]->(b:Organization)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_interested_in='''
MATCH (a:Consumer)-[rel:interested_in]->(b:Event)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_wishlisted='''
MATCH (a:Consumer)-[rel:wishlisted]->(b:Product)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_basketed='''
MATCH (a:Consumer)-[rel:basketed]->(b:Product)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_has_presence_at='''
MATCH (a:Community)-[rel:has_presence_at]->(b:Location)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_hosting='''
MATCH (a:Community)-[rel:hosting]->(b:Event)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_happening_at='''
MATCH (a:Event)-[rel:happening_at]->(b:Location)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_branched='''
MATCH (a:Organization)-[rel:branched]->(b:Location)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

get_available_at='''
MATCH (a:Product)-[rel:available_at]->(b:Location)
WHERE a.uuid = $uuid1 AND b.uuid = $uuid2
RETURN id(rel)
'''

#Get the product's details
get_product_details='''
MATCH (p:Product)-[rel:available_at]->(l:Location)
WHERE p.uuid = $uuidp AND l.uuid = $uuidl
RETURN rel
'''

get_partner='''
MATCH (org:Organization)-[rel:partner]-(par:Organization)
WHERE org.uuid = $uuido AND par.uuid = $uuidp
RETURN rel
'''

get_all_partners='''
MATCH (org:Organization)-[rel:partner]-(par:Organization)
WHERE org.uuid = $uuid
RETURN rel, par
'''

get_loyalty_tracker='''
MATCH (c:Consumer)-[rel:loyalty_tracker]->(o:Organization)
WHERE c.uuid = $uuidc AND o.uuid = $uuido
RETURN rel
'''

unique_wishlist='''
MATCH (c:Consumer)-[rel:wishlisted]->(p:Product)
WHERE c.uuid = $uuidc AND p.uuid = $uuidp
DELETE rel
'''

unique_basket='''
MATCH (c:Consumer)-[rel:basketed]->(p:Product)
WHERE c.uuid = $uuidc AND p.uuid = $uuidp
DELETE rel
'''

unique_partner='''
MATCH (org:Organization)-[rel:partner]-(par:Organization)
WHERE org.uuid = $uuido AND par.uuid = $uuidp
DELETE rel
'''

get_raincheck_id_from_tied_to='''
MATCH (r:Raincheck)-[rel:tied_to]->(c:Consumer)
WHERE c.uuid = $uuid
RETURN id(r)
'''

get_consumer_purchases='''
MATCH (c:Consumer)-[b:bought]->(p:Purchase)
WHERE c.uuid = $uuid
return p
'''

get_location_org='''
MATCH (l:Location)<-[b:branched]-(o:Organization)
WHERE l.uuid = $uuid
RETURN o
'''

get_flyer='''
MATCH (p:Product)-[aa:available_at]->(l:Location)
WHERE l.uuid = $uuid AND aa.on_flyer = 'True'
RETURN p
'''

get_requested_partners = '''
MATCH (o:Organization)-[pp:pending_partner]->(p:Organization)
WHERE o.uuid = $uuid
RETURN p
'''

get_partner_requests = '''
MATCH (o:Organization)-[pp:pending_partner]->(p:Organization)
WHERE p.uuid = $uuid
RETURN o
'''

get_pending_partner ='''
MATCH (o:Organization)-[pp:pending_partner]->(p:Organization)
WHERE o.uuid = $uuido AND p.uuid = $uuidp
RETURN pp
'''

get_employee_organization='''
MATCH (e:Employee)-[wa:works_at]->(l:Location)<-[b:branched]-(o:Organization)
WHERE e.uuid = $uuid
RETURN o
'''

get_temp_deal_availability='''
MATCH (p:Product)-[rel:temp_deal]->(l:Location)
WHERE p.uuid = $uuidp AND l.uuid = $uuidl
RETURN rel
'''

get_temp_deal_by_code='''
MATCH (p:Product)-[td:temp_deal]->(l:Location)
where td.code = $code
return td, p.uuid, l.uuid
'''

get_community_count='''
MATCH (c:Consumer)-[:is_member_of]->(t:Community)
WHERE t.uuid = $uuid
RETURN count(c)
'''

get_community_members='''
MATCH (c:Consumer)-[:is_member_of]->(t:Community)
WHERE t.uuid = $uuid
RETURN c
'''

get_temp_deal_by_org='''
MATCH (p:Product)-[td:temp_deal_org]->(l:Location)
where td.organization_uuid = $uuid
return td, p.uuid, l.uuid
'''