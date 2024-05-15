# a test sample file for integration
import extract_callgraph
import gen_callgraph

if __name__ == "__main__":
    if not gen_callgraph.main():
        exit(1)
    extract_callgraph.main()
