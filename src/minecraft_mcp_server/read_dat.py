# from nbt import nbt

# player = nbt.NBTFile('./6b4cdefd-9c44-447b-8776-6e609722867e.dat','rb')

# print(player.pretty_tree())


import sys 
import json , re
from nbt import nbt
# Import the NBT tag types we need to convert
from nbt.nbt import (
    TAG_Compound, TAG_List,
    TAG_Byte_Array, TAG_Int_Array, TAG_Long_Array,
    TAG_Byte, TAG_Short, TAG_Int, TAG_Long,
    TAG_Float, TAG_Double, TAG_String
)

# Group the types for easier checking
# These all just need to be converted to their .value
SCALAR_TAGS = (
    TAG_Byte, TAG_Short, TAG_Int, TAG_Long,
    TAG_Float, TAG_Double, TAG_String
)

# These need to be converted to a list of their .value
ARRAY_TAGS = (
    TAG_Byte_Array, TAG_Int_Array, TAG_Long_Array
)


class NBTEncoder(json.JSONEncoder):
    """
    A custom JSON encoder that correctly handles ALL NBT tag types.
    """
    def default(self, obj):
        
        # --- THIS IS THE FIX ---
        # Convert simple NBT tags (TAG_Int, TAG_Float, etc.)
        # to their underlying Python value.
        if isinstance(obj, SCALAR_TAGS):
            return obj.value
        
        # Convert NBT container types to Python dicts and lists
        if isinstance(obj, TAG_Compound):
            return dict(obj)
        if isinstance(obj, TAG_List):
            return list(obj)
        
        # Convert NBT array types to a plain Python list
        if isinstance(obj, ARRAY_TAGS):
            return list(obj.value)

        # Let the base class raise a TypeError for any unhandled types
        return super().default(obj)

try:
    # Load your NBT file
    player = nbt.NBTFile('./test.dat', 'rb')

    # Dump the NBT object to a JSON string
    # - cls=NBTEncoder tells json.dumps to use our custom converter
    # - indent=2 makes the output pretty-printed (like jq)
    json_output = json.dumps(player, cls=NBTEncoder, indent=2)
    json_output = re.sub("NaN","null", json_output)
    
    with open('player.json','w+') as f:
        f.write(json_output)

        

    # Print the final JSON string
    # print(json_output)
    
    

except FileNotFoundError:
    print("Error: './somedat.dat' not found.", file=sys.stderr)
except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)