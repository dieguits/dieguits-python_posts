
# dict = {"name": "diego", "age": 34, "city": "Bucaramanga"}

# for index, value in dict.items():
#     print(f" Index: {index}")
#     print(f" Value: {value}")
    
    
# array = ["diego", 89, "Bucaramanga", False]

# for value in range(len(array)):
#     print(array[value])
    
# tuple = (3, 4 , 5)
# tuple2 = (1, 2, 6)
# dict = {"some": 9}
# result = tuple + tuple2
# print(result)

# for value in enumerate(array, len(array)-1):
#     print(f"The index here: {value[0]}")
#     print(f"The value here: {value[1]}")
    
def validation(value):
    index = 0
    for val in value:
        print(val)
        
        if index == 0 and (val == ')' or val == '}' or val == ']'):
            return False 
    
    
definition = {"((){}[])"}

validation(definition)