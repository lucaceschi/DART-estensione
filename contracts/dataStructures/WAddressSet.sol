pragma solidity >=0.8.1 <0.9;

library WAddressSet {

	struct Set {
		mapping(address => uint) map;
		bytes21[] list;
	}

	function packEntry(address _member, uint8 _weight) internal pure returns(bytes21 result) {
		bytes memory packed = abi.encodePacked(_member, _weight);
		assembly {
			result := mload(add(packed, 32))
		}
	}

	function insert(Set storage self, address _member, uint8 _weight) internal returns(bool) {
		uint pointer = self.map[_member];

		if(pointer != 0) {
			if(uint8(bytes1(self.list[pointer - 1] << 160)) < _weight) {
				self.list[pointer - 1] = packEntry(_member, _weight);
				return true;
			}
			else
				return false;
		}

		self.list.push(packEntry(_member, _weight));
		pointer = size(self);
		self.map[_member] = pointer;
		return true;
	}

	function update(Set storage self, address _member, uint8 _weight) internal {
		uint pointer = self.map[_member];
		require(pointer != 0, "entry not found");

		self.list[pointer - 1] = packEntry(_member, _weight);
	}

	function remove(Set storage self, address _member) internal {
		uint pointerToRemove = self.map[_member];
		require(pointerToRemove != 0, "entry not found");
		uint lastPointer = size(self);

		if(pointerToRemove != lastPointer) {
			bytes21 lastEntry = self.list[lastPointer - 1];
			self.list[pointerToRemove - 1] = lastEntry;
			self.map[address(bytes20(lastEntry))] = pointerToRemove;

		}
		self.list.pop();
		self.map[_member] = 0;
	}

	function size(Set storage self) internal view returns(uint) {
		return self.list.length;
	}

	function exists(Set storage self, address _member) internal view returns(bool) {
		uint pointer = self.map[_member];
		return pointer != 0;
	}

	function getPointer(Set storage self, address _member) internal view returns(uint) {
		return self.map[_member];
	}

	function getWeight(Set storage self, uint _index) internal view returns(uint8) {
		return uint8(bytes1(self.list[_index] << 160));
	}

	function get(Set storage self, uint _index) internal view returns(address, uint8) {
		bytes21 entry = self.list[_index];
		return (address(bytes20(entry)), uint8(bytes1(entry << 160)));
	}

}
