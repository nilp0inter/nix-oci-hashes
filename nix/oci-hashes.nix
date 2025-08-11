{ self, lib, ... }:

{
  flake = {
    ociHashes = 
      let
        digestsFile = self + "/digests.json";
        
        # Read the digests.json file if it exists
        digests = if builtins.pathExists digestsFile then
          builtins.fromJSON (builtins.readFile digestsFile)
        else
          {};
      in
        digests;
  };
}