{ self, lib, ... }:

{
  flake = {
    ociHashes = 
      let
        parseDockerfile = path:
          let
            content = builtins.readFile path;
            lines = lib.splitString "\n" content;
            fromLine = lib.findFirst (line: lib.hasPrefix "FROM " line) "" lines;
            extractImage = line:
              if lib.hasPrefix "FROM " line then
                lib.removeSuffix "\n" (lib.removeSuffix "\r" (lib.removePrefix "FROM " line))
              else
                null;
          in
            extractImage fromLine;

        processDockerDir = dockerDir:
          let
            topLevelDirs = builtins.readDir dockerDir;
            
            processTopLevel = dirName: dirType:
              if dirType == "directory" then
                let
                  dirPath = dockerDir + "/${dirName}";
                  projects = builtins.readDir dirPath;
                in
                  lib.mapAttrs (projectName: projectType:
                    if projectType == "directory" then
                      let
                        projectPath = dirPath + "/${projectName}";
                        versions = builtins.readDir projectPath;
                      in
                        lib.mapAttrs (version: versionType:
                          if versionType == "directory" then
                            let
                              dockerfilePath = projectPath + "/${version}/Dockerfile";
                            in
                              if builtins.pathExists dockerfilePath then
                                parseDockerfile dockerfilePath
                              else
                                null
                          else
                            null
                        ) versions
                    else
                      null
                  ) projects
              else
                null;
            
            allResults = lib.mapAttrs processTopLevel topLevelDirs;
            
            mergeByProject = 
              let
                getAllProjects = lib.foldl' (acc: dirResults:
                  if dirResults != null then
                    acc ++ (lib.attrNames dirResults)
                  else
                    acc
                ) [] (lib.attrValues allResults);
                
                uniqueProjects = lib.unique getAllProjects;
                
                mergeProject = projectName:
                  let
                    versionsFromAllDirs = lib.foldl' (acc: dirResults:
                      if dirResults != null && dirResults ? ${projectName} then
                        acc // dirResults.${projectName}
                      else
                        acc
                    ) {} (lib.attrValues allResults);
                  in
                    lib.filterAttrs (n: v: v != null) versionsFromAllDirs;
              in
                lib.genAttrs uniqueProjects mergeProject;
          in
            mergeByProject;

        # Process both old structure and new structure
        oldHashes = if builtins.pathExists (self + "/dockers") then
          processDockerDir (self + "/dockers")
        else {};
        
        pinsHashes = if builtins.pathExists (self + "/nix/_dockerfiles/pins") then
          processDockerDir (self + "/nix/_dockerfiles/pins")
        else {};
      in
        # Merge both, with pins taking precedence
        lib.recursiveUpdate oldHashes pinsHashes;
  };
}