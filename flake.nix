{
  description = "OCI/Docker image hashes extracted from Dockerfiles";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      lib = nixpkgs.lib;

      # Parse a Dockerfile to extract everything after FROM
      parseDockerfile = path:
        let
          content = builtins.readFile path;
          lines = lib.splitString "\n" content;
          fromLine = lib.findFirst (line: lib.hasPrefix "FROM " line) "" lines;
          # Extract everything after "FROM "
          extractImage = line:
            if lib.hasPrefix "FROM " line then
              # Remove "FROM " prefix and any trailing whitespace/newlines
              lib.removeSuffix "\n" (lib.removeSuffix "\r" (lib.removePrefix "FROM " line))
            else
              null;
        in
          extractImage fromLine;

      # Process the docker directory structure
      processDockerDir = dockerDir:
        let
          # Read all subdirectories (major, major-minor, etc.)
          topLevelDirs = builtins.readDir dockerDir;
          
          # Process each top-level directory
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
          
          # Get all results from different top-level directories
          allResults = lib.mapAttrs processTopLevel topLevelDirs;
          
          # Merge results by project name
          mergeByProject = 
            let
              # Collect all project names
              getAllProjects = lib.foldl' (acc: dirResults:
                if dirResults != null then
                  acc ++ (lib.attrNames dirResults)
                else
                  acc
              ) [] (lib.attrValues allResults);
              
              uniqueProjects = lib.unique getAllProjects;
              
              # For each project, merge versions from all directories
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
    in
    {
      ociHashes = processDockerDir ./dockers;
    };
}
