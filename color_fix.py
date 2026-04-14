import os

file_path = r"c:\Users\MrVamsiKasireddy\Desktop\Tasks\Pre-Appointment_Agent\templates\agent_workspace.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace purple gradient with requested blue gradient (#355872 to #7AAACE)
content = content.replace("linear-gradient(135deg,#7c6af7,#a78bfa)", "linear-gradient(135deg,#355872,#7AAACE)")
content = content.replace("linear-gradient(135deg, #7c6af7, #a78bfa)", "linear-gradient(135deg, #355872, #7AAACE)")

# Replace purple rgba with #355872 rgba (53, 88, 114)
content = content.replace("rgba(124,106,247,0.15)", "rgba(53,88,114,0.15)")
content = content.replace("rgba(124,106,247,0.08)", "rgba(53,88,114,0.08)")
content = content.replace("rgba(124,106,247,0.1)", "rgba(53,88,114,0.1)")
content = content.replace("rgba(124,106,247,0.2)", "rgba(53,88,114,0.2)")
content = content.replace("rgba(124,106,247,0.3)", "rgba(53,88,114,0.3)")

# Replace hardcoded dark mode colors
content = content.replace("background: #1e1b2e;", "background: #FFFFFF;")
content = content.replace("rgba(255,255,255,0.06)", "rgba(53,88,114,0.15)")

# Replace loading spinner colors
content = content.replace("border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;", "border: 2px solid rgba(53,88,114,0.3); border-top-color: #355872;")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated HTML colors")
