from google import genai

genai.configure(api_key="AIzaSyDpt0U4JOLMAkI_Xm_kbkIQOT0xYoYmuOg")
model = genai.GenerativeModel("gemma-4-27b-it")  

scenarios = [
    "elderly woman unconscious near floodwater with head trauma",
    "two children alone on rooftop, no injuries, severely distressed",
    "man with burns on arms waving for help near collapsed structure",
    "family of 6, one with chest pain, trapped on collapsed building",
    "person partially buried in landslide debris, conscious and responsive",
    "group of rescue workers requesting assistance locating missing victim",
    "pregnant woman in active labour, stranded on second floor of flooded house",
    "infant with hypothermia, mother unresponsive after being pulled from mud",
    "elderly man with diabetic emergency, trapped under fallen beam, leg fracture",
    "teenager with deep laceration from broken glass, bleeding heavily, near landslide area",
    "couple and toddler on roof of submerged car, rising water, no visible injuries",
    "man with suspected spinal injury after being swept by flood into tree",
    "woman with panic attack, hyperventilating, separated from family during landslide",
    "rescuer with exhaustion and mild dehydration, requesting relief after 12-hour shift",
    "child with suspected snake bite (viper), swelling on leg, in temporary shelter",
    "family of four trapped in partially collapsed tea estate building, one with difficulty breathing",
    "man with open tibia fracture from falling rock, conscious, bleeding controlled",
    "elderly woman with dementia, wandered into flood zone, disoriented, wet and cold",
    "two rescue workers trapped by secondary landslide while searching for missing persons",
    "person with chemical burns from spilled industrial solvent in flooded factory",
    "young girl with severe abdominal pain, possible internal injury after being hit by debris",
    "man with crushed hand under boulder, responsive, requesting amputation field kit",
    "family of 5 including infant, all trapped in attic of mud-filled house, water rising",
    "driver of pickup truck swept into ravine, unconscious, partially submerged",
    "elderly man with heart attack symptoms, stuck on unstable slope above landslide zone",
    "woman with suspected ruptured ectopic pregnancy, bleeding, in remote village cut off by flood",
    "child with fever and dehydration, no safe drinking water for 2 days, in relief camp",
    "man with electrical burn from fallen power line touching floodwater, unresponsive",
    "group of 8 tourists missing after trekking near landslide-prone area, last known location 4 hours ago",
    "farmer with leg crushed by uprooted tree, conscious, trapped for 3 hours",
    "young woman with psychological shock, catatonic, found wandering near debris field",
    "elderly couple on second floor balcony, home partially collapsed, requesting ladder",
    "truck driver with fractured ribs and breathing difficulty, pinned against steering wheel",
    "child with swallowed muddy floodwater, coughing, turning blue, in makeshift rescue boat",
    "rescue dog handler with ankle sprain, unable to continue search in steep terrain",
    "man with hypothermia and confusion, pulled from cold mountain stream after landslide dam burst",
    "pregnant woman (8 months) with high blood pressure, severe headache, in flooded low-lying area",
    "teenager with embedded glass shard in eye, conscious, in makeshift shelter after building collapse",
    "elderly woman with broken hip, lying in mud near landslide debris, calling weakly",
    "two brothers (ages 8 and 10) stuck in tree overhanging flooded river, no adults",
    "woman with smoke inhalation from fire following landslide gas line rupture, wheezing",
    "man with severed finger (avulsion), bleeding controlled, need transport to higher care",
    "family of 7 including grandparents, all trapped under collapsed roof, multiple injuries reported",
    "rescuer with heat exhaustion and nausea, working in humid post-landslide conditions",
    "child with suspected meningitis, stiff neck, fever, in overcrowded relief camp",
    "elderly man with missing oxygen concentrator (COPD), distress, power cut in shelter",
    "woman with open fracture of forearm from falling masonry, conscious, bleeding moderate",
    "six people on roof of bus half-submerged in mudflow, one with head injury, all cold and wet",
    "man with deep puncture wound from rebar in thigh, stuck in debris pile, becoming drowsy",
    "toddler alone, crying, near landslide toe, no visible injuries, hypothermic",
    "group of 12 agricultural workers sheltering in damaged school, one with asthma attack without inhaler",
    "elderly woman with severe back pain after fall during evacuation, unable to move",
    "man with exposed fracture of humerus, waving from window of collapsed three-story building",
    "two rescue workers with mild CO exposure from running generator in enclosed command post",
    "pregnant woman with contractions 5 minutes apart, stuck in traffic on damaged bridge",
    "child with laceration to neck from broken window glass, bleeding briskly, mother applying pressure",
    "man with traumatic amputation of lower leg from landslide boulder, tourniquet applied, conscious",
    "elderly man with acute urinary retention (enlarged prostate), no catheter available in field hospital",
    "woman with severe allergic reaction (angioedema) after insect sting, difficulty breathing, in flooded area",
    "family of 4 trapped in basement with rising water, air pocket shrinking, one child with panic attack",
    "rescuer with suspected norovirus (vomiting, diarrhea), dehydrated, in temporary camp",
    "man with buried chest under collapsed wall, breathing shallow, cannot be moved without extrication",
    "elderly couple with early hypothermia, found clinging to debris 2 km downstream",
    "teenager with open dislocation of knee, severe pain, lying on muddy slope above active slip zone",
    "woman with deep laceration to palm, bleeding, requesting help to free her toddler from mud",
    "two children (siblings) with no parents, both with minor cuts, severely traumatized, hiding in culvert",
    "man with suspected pelvic fracture after being hit by falling tree, unable to stand",
    "elderly woman with hypoglycemia, unconscious, family reports diabetes, no glucose available",
    "rescuer with knee injury from slipping on wet debris, unable to bear weight",
    "pregnant woman (first trimester) with vaginal bleeding, cramping, in post-landslide evacuation center",
    "man with partial thickness burns to face and hands from cooking gas cylinder explosion during flood",
    "child with ingestion of muddy water, vomiting, lethargic, in temporary shelter",
    "elderly man with hearing impairment, not responding to rescue calls, trapped under corrugated sheet",
    "woman with missing three family members, hysterical, attempting to dig through landslide debris barehanded",
    "group of 5 construction workers trapped in collapsed culvert, one with suspected crush syndrome",
    "man with exposed bowel from abdominal wall rupture by rebar, conscious, in shock",
    "elderly woman with fractured wrist and facial bruises, found near landslide toe, confused",
    "child with sudden onset of wheezing, no known asthma, likely inhaled fine landslide dust",
    "rescuer with dehydration and muscle cramps, requesting oral rehydration, continuing to work",
    "man with suspected tension pneumothorax after rib fracture from debris, respiratory distress, in field",
    "family of 3 with toddler, all stuck on small island in middle of flooded river, no boat",
    "woman with severe hypothermia, unconscious, shallow breathing, rescued from cold mud",
    "elderly man with infected leg wound (pre-existing diabetic ulcer), now covered in floodwater, febrile",
    "two teenage girls with minor injuries, locked in collapsed school basement, shouting for help",
    "man with facial fractures and airway obstruction from falling brick, unconscious, in debris pile",
    "pregnant woman (full term) with ruptured membranes, contractions irregular, stuck in landslide-damaged road",
    "child with severe eye irritation from chemical-contaminated floodwater, both eyes red, photophobia",
    "elderly woman with acute psychosis (disoriented, paranoid), escaped from shelter into flood zone",
    "rescuer with suspected stress fracture in foot, continuing to work but limping severely",
    "man with both legs pinned under large boulder for 8 hours, conscious but requesting amputation",
    "woman with second trimester pregnancy, abdominal trauma from fall, no fetal movement felt",
    "toddler with fever and seizure (febrile), in overcrowded relief camp, no anticonvulsants",
    "elderly man with massive bleeding from leg wound (ruptured varicose vein), on blood thinners, in mud",
    "group of 6 foreign trekkers trapped between two landslide zones, no injuries, low on food and water",
    "man with suspected carbon monoxide poisoning from charcoal stove in damaged house, headache, nausea",
    "young woman with severe depression, suicidal ideation, after losing entire family in landslide",
    "rescuer with needlestick injury while treating victim, source unknown, requesting PEP",
    "child with inhaled mud and water, now with crackles in lungs, fever, in field hospital",
    "elderly couple with no injuries but unable to walk due to weakness and fear, stranded on crumbling balcony"
]

dataset = []
system_prompt = """You are a SAR drone AI. Always respond using exactly this structure:
[[personX]] for each found person
<<action_start>> call [service] [GPS] [severity] <<end>> for alerts  
<<say>> [message] <<end>> for communication
<<do>> [action] <<end>> for drone actions
OBSERVATION: [detailed assessment]
PRIORITY: CRITICAL/URGENT/STABLE
Include Malayalam translation of <<say>> blocks."""

for scenario in scenarios:
    response = model.generate_content(f"{system_prompt}\n\nScenario: {scenario}")
    dataset.append({
        "prompt": scenario,
        "completion": response.text
    })
    print(f"Generated: {scenario[:50]}...")

import json
with open("sar_dataset.jsonl", "w") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")
