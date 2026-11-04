Output docs/demo/generate.gif
Source docs/demo/common.tape

Hide
Type "Remove-Item -ErrorAction Ignore person.schema.json; Clear-Host"
Enter
Show

Type "schemify generate -t Person -o person.schema.json"
Sleep 300ms
Enter
Sleep 2s

# first: string, label, required
Type "first" Enter Sleep 400ms Enter Sleep 400ms Enter Sleep 400ms
Type "First name" Enter Sleep 300ms Enter Enter Sleep 300ms Enter Sleep 600ms

# last
Type "last" Enter Sleep 400ms Enter Sleep 400ms Enter Sleep 400ms
Type "Last name" Enter Sleep 300ms Enter Enter Sleep 300ms Enter Sleep 600ms

# age: integer, optional
Type "age" Enter Sleep 400ms Up Sleep 200ms Up Sleep 200ms Up Sleep 400ms Enter Sleep 400ms Enter Sleep 400ms
Enter Enter Enter Sleep 400ms
Type "n" Sleep 600ms

# full_name: computed with join
Type "full_name" Enter Sleep 400ms Down Sleep 400ms Enter Sleep 600ms
Enter Sleep 800ms
Space Sleep 300ms Down Sleep 300ms Space Sleep 400ms Enter Sleep 400ms
Enter Sleep 300ms Enter Sleep 300ms Enter Sleep 300ms
Type "Full name" Enter Sleep 300ms Enter Sleep 300ms Enter Sleep 600ms

# finish, no extra properties
Enter Sleep 400ms Enter
Sleep 1500ms

Type "Get-Content person.schema.json"
Enter
Sleep 4s
