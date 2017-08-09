from csv import reader
from copy import deepcopy
import numpy as np
from sys import argv

#import arguments
a, input_text, output_text, n_iterations = argv

class Transition:
    """Represents a single set of transitions, with a condition"""
    def __init__(self, trans_cond, probs, trans_states):
        self.trans_cond = trans_cond
        self.probs = probs
        self.trans_states = trans_states

    def matches_cond(self, grounding, attributes):
        if self.trans_cond == 'Default':
            return True
        
        cond_split = self.trans_cond.replace('.', ' ').split(' ')
        cond_fill = attributes[grounding[cond_split[0]]][cond_split[1]]
        if not cond_fill.isnumeric():
            cond_fill = "\"" + cond_fill + "\""
        cond_split[0] = cond_fill
        cond_split[1] = ''
        return eval(''.join(cond_split))

class State:
    """Represents a state with text and a list of possible transition sets"""
    def __init__(self, text, trans_list):
        self.text = text
        self.trans_list = trans_list

    def sample_next(self, grounding, attributes):
        i = 0
        while not self.trans_list[i].matches_cond(grounding, attributes):
            i += 1
        probs = self.trans_list[i].probs
        trans_states = self.trans_list[i].trans_states
        return np.random.choice(trans_states, p=probs)
        
            

attributes = dict()
entities = dict()
roles = dict()
states = dict()

f = open(input_text)

# Read entities
assert f.readline().strip() == "Entities", "Spec file must start with Entities"
f.readline()  # Dashed line
while True:
    nextline = f.readline().strip()
    if nextline == 'Roles':
        break
    ent_spec = nextline.split(':')
    ent_name = ent_spec[0]
    ent_attr = [x.strip() for x in ent_spec[1].split(',')]
    entities[ent_name] = []

    inst_line = f.readline().strip()
    while inst_line:
        # Use csv reader here, to ignore commas inside quotes
        instance = [x for x in reader([inst_line], skipinitialspace=True)][0]
        assert len(instance) == len(ent_attr), "Instance %s does not match entity spec" % instance[0]
        entities[ent_name].append(instance[0])
        attributes[instance[0]] = dict()
        for i, a in enumerate(ent_attr):
            attributes[instance[0]][a] = instance[i]
        inst_line = f.readline().strip()

# Read roles
f.readline() # Dashed line
role_line = f.readline().strip()
while role_line:
    role = [x.strip() for x in role_line.split(':')]
    roles[role[0]] = role[1]
    role_line = f.readline().strip()

# Read States
assert f.readline().strip() == "States", "States must follow Roles"
f.readline() # Dashed line
while True:
    state_name = f.readline().strip()
    text = f.readline().strip()

    if state_name == "END":
        states[state_name] = State(text, [])
        break

    trans_list = []
    trans_line = f.readline().strip()
    while trans_line:
        trans_split = trans_line.split(':')
        trans_cond = trans_split[0]
        probs = []
        trans_states = []
        assert len(trans_split) == 2, "Transition should have one colon - %s" % trans_line
        for x in trans_split[1].split(','):
            [p,s] = x.strip().split(' ')
            probs.append(p)
            trans_states.append(s)
        probs = np.array(probs).astype(np.float)
        trans_list.append(Transition(trans_cond, probs, trans_states))
        trans_line = f.readline().strip()
    states[state_name] = State(text, trans_list)
f.close()        



# Generate stories
f = open(output_text,'w')
for i in range(int(n_iterations)):
    # Create Grounding
    np.random.seed(i)
    grounding = dict()
    avail_entities = deepcopy(entities)
    for role in sorted(roles.keys()):
        grounding[role] = np.random.choice(avail_entities[roles[role]])
        avail_entities[roles[role]].remove(grounding[role])

    # Loop through states
    curr_state = 'BEGIN'
    while True:
        # Output state text with fillers
        text_split = states[curr_state].text.replace(']','[').split('[')
        for i in range(1,len(text_split),2):
            slot = text_split[i].split('.')
            text_split[i] = attributes[grounding[slot[0]]][slot[1]]
        filled = ''.join(text_split)
        if filled[0] == "\"":
            filled = filled[0] + filled[1].upper() + filled[2:]
        else:
            filled = filled[0].upper() + filled[1:]
        f.write(filled)
        f.write(" ")
            
        if curr_state == 'END':
            f.write("\n\n")
            break

        # Sample next state
        curr_state = states[curr_state].sample_next(grounding, attributes)

f.close()