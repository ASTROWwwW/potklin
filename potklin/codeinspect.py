"""Local Python syntax and symbol inventory, never executes target code."""
import ast

def symbols(workspace,path):
    data=workspace.read(path)["text"]
    try:
        tree=ast.parse(data)
    except SyntaxError as e:
        return {"path":path,"valid":False,"line":e.lineno}
    nodes=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            nodes.append({"name":node.name,"kind":type(node).__name__,"line":node.lineno})
    return {"path":path,"valid":True,"symbols":sorted(nodes,key=lambda n:n["line"])[:500]}
