states = ""
with open("items.txt") as f:
    data=f.read().replace('\n', '')
'''
with open("items.txt") as f:
    content = f.readlines()
    for c in content:
        states = states + c + '|'
'''
print data

'''
with open("items.txt") as f:
    data=f.read().replace('\n', '')
'''
