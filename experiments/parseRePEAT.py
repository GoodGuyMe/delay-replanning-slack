def parse_repeat(s):
    #s is a string with the text output of a repeat search this parses it into the compount atf, and the individual augmentded SIPP plans for each segment
    s = s.strip("\n").split("\n") # avoid empty element in list
    return parse_list_of_outputs(s)

def parse_list_of_outputs(s):
    # s is the output split on newline characters
    i = 0
    while "Nodes generated" not in s[i]:
        i += 1
    metadata = s[i]
    i+=1
    catf = s[i].strip(", ").split(", ") # avoid empty element in list
    catf = [tuple(x.strip("'").strip("<").strip(">").split(",")) for x in catf]
    i += 1
    paths = []
    eatfs = []
    while i < len(s) and "time: " not in s[i]:
        paths.append([])
        while "time: " not in s[i] and (s[i][0] != "<") and (s[i][-1] != ">"):
            # s[i]: "node_name node_safe_interval node_id"
            paths[-1].append(s[i].split(" ")[0])
            i += 1
        atf = s[i]
        atf = tuple(atf.strip("<").strip(">").split(","))
        eatfs.append(atf)
        i += 1
    if [] in paths:
        paths.remove([]) # because the last path added stays empty
    unique_paths = {}
    unique_path_eatfs = {}
    for (i,p) in enumerate(paths):
        path_string = ";".join(p)
        if path_string in unique_paths:
            unique_paths[path_string] += 1
            if eatfs[i] not in unique_path_eatfs[path_string]:
                unique_path_eatfs[path_string].append(eatfs[i])
        else:
            unique_paths[path_string] = 1
            unique_path_eatfs[path_string] = [eatfs[i]]

    return metadata, catf, unique_paths, unique_path_eatfs


def test():
    parse_list_of_outputs(
        ['Arrival time: 130.667', 'Nodes generated: 10 Nodes decreased: 0 Nodes expanded: 8', '<-inf,20,130.667,130.667>, <20,50,130.667,160.667>, <50,inf,inf,inf>, ', 't-EHB <0,50> ns:1', 's-123BL <0,150> ns:2', 's-125BR <93,160> ns:2', 's-131B <88,170> ns:2', 't-401B <115,2000> ns:1', 't-401A <115,2000> ns:2', '<-inf,20,50,110.667>', 't-EHB <0,50> ns:1', 's-123BL <0,150> ns:2', 's-125BR <93,160> ns:2', 's-131B <88,170> ns:2', 't-401B <115,2000> ns:1', 't-401A <115,2000> ns:2', '<-inf,20,50,110.667>', '<0,0,inf,inf>', 'Search time: 1141791 nanoseconds', 'Total (n=100) Lookup time: 10917 nanoseconds']
)
# run $ python3 -c 'from parseRePEAT import *; test()'
