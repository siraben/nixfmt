import Control.Exception
import Control.Monad
import System.Directory
import System.Environment
import System.IO
import System.IO.Atomic
import System.Posix.Files

main :: IO ()
main = do
  [dir] <- getArgs
  let path = dir ++ "/target.nix"
  _ <- setFileCreationMask 0o022
  withOutputFile path $ \h -> do
    [temporary] <- listDirectory dir
    mode <- fileMode <$> getFileStatus (dir ++ "/" ++ temporary)
    unless (mode `mod` 0o1000 == 0o600) $ error "temporary file is not private"
    hPutStr h "first"
  setFileMode path 0o640
  withOutputFile path $ \h -> hPutStr h "second"
  mode <- fileMode <$> getFileStatus path
  unless (mode `mod` 0o1000 == 0o640) $ error "target mode was not preserved"
  _ <- try (withOutputFile path $ \h -> hPutStr h "bad" >> ioError (userError "abort")) :: IO (Either IOException ())
  value <- readFile path
  unless (value == "second") $ error "rollback changed target"
  files <- listDirectory dir
  unless (files == ["target.nix"]) $ error "rollback leaked temporary file"
  putStrLn "PASS: private creation, mode preservation, rollback and cleanup"
