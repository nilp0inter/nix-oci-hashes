{ self, lib, ... }:

{
  perSystem = { config, pkgs, system, ... }: {
    packages = {
      # Unified manage-images script
      manage-images = pkgs.writers.writePython3Bin "manage-images" {
        libraries = [ ];
        flakeIgnore = [ "E501" "E265" ];
      } (builtins.readFile ./scripts/manage-images.py);

      ci-env = pkgs.buildEnv {
        name = "nix-oci-hashes-ci-env";
        paths = with pkgs; [
          config.packages.manage-images
          git
          jq
        ];
      };
    };

    devShells.default = pkgs.mkShell {
      buildInputs = with pkgs; [
        config.packages.manage-images
        python3
        git
        jq
      ];
    };
  };
}