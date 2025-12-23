
# Legacy code with issues
def old_function(x,y,z):
    if x==1:
        if y==2:
            if z==3:
                return True
    return False

# Global variables (bad practice)
global_var = "bad"

def another_function():
    # No documentation
    # Complex nested logic
    result = []
    for i in range(10):
        if i % 2 == 0:
            for j in range(5):
                if j < 3:
                    result.append(i*j)
    return result
