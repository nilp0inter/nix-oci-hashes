{ self, lib, ... }:

{
  perSystem = { config, pkgs, system, ... }: {
    packages = {
      generate-version-dockerfiles = pkgs.writers.writePython3Bin "generate-version-dockerfiles" {
        libraries = [ pkgs.python3Packages.pyyaml ];
        flakeIgnore = [ "E501" "E265" ];
      } (builtins.readFile ./scripts/generate-version-dockerfiles.py);

      harvest-tags = pkgs.writers.writePython3Bin "harvest-tags" {
        libraries = [ ];
        flakeIgnore = [ "E501" "E265" ];
      } (builtins.readFile ./scripts/harvest-tags.py);

      ci-env = pkgs.buildEnv {
        name = "nix-oci-hashes-ci-env";
        paths = with pkgs; [
          config.packages.generate-version-dockerfiles
          config.packages.harvest-tags
          git
          jq
        ];
      };
    };

    devShells.default = pkgs.mkShell {
      buildInputs = with pkgs; [
        config.packages.generate-version-dockerfiles
        config.packages.harvest-tags
        python3
        python3Packages.pyyaml
        git
        jq
      ];
    };
  };
}